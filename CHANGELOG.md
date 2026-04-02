# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-02

### 追加 (Added)
- パッケージ基本情報
  - 初期バージョンとして kabusys パッケージを公開。バージョンは `0.1.0`。
  - パッケージ公開 API: data, strategy, execution, monitoring を `__all__` でエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト等向け）。
  - .env パーサーを独自実装
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント扱いの細かいルール等をサポート。
    - 読み込み失敗時は警告を出力して継続。
  - 環境設定用の `Settings` クラスを提供（`settings` をエクスポート）。
    - J-Quants / kabuステーション / Slack / データベース / 監視 / システム設定などをプロパティで取得。
    - 必須環境変数未設定時は `ValueError` を送出する `_require` を採用。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェックを実装（値検証で早期検出）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results の有無、コード一致、数値検査）を行い、スコアを ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルに置換的に保存（DELETE → INSERT）。部分失敗時に既存データを保護する設計。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部の `_call_openai_api` を patch）。
    - ルックアヘッドバイアス防止のため内部で datetime.today() を参照しない実装（ターゲット日ベース）。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - 日経225 連動 ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - DuckDB の prices_daily / raw_news / market_regime を参照してスコアを計算し、冪等で market_regime テーブルに書き込み。
    - LLM 呼び出し（OpenAI）失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - API 呼び出しに対するリトライ・バックオフ・エラー種別処理を実装。
    - テスト用に OpenAI 呼び出しを差し替え可能。

- 研究系モジュール (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、MA200乖離）、Value（PER/ROE）、Volatility（20日 ATR）等の定量ファクター計算を実装。
    - DuckDB を用いた SQL ベースの実装。prices_daily / raw_financials のみ参照し、本番口座や発注 API にはアクセスしない設計。
    - 出力は (date, code) をキーとする辞書リスト。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク付けユーティリティを提供。
    - 外部ライブラリに依存せず純粋 Python / DuckDB で実装。
    - 入力検証（horizons の制約、最小サンプル数等）を実施。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末非営業扱い）。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得 → 冪等保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline.ETLResult を kabusys.data.etl で再公開)
    - データ差分取得 → 保存 → 品質チェック のワークフロー設計に基づく ETLResult データクラスを実装。
    - ETLResult は取得・保存件数、品質問題、エラー集約や has_errors / has_quality_errors 判定、辞書化(to_dict) をサポート。
    - デフォルトのバックフィルや最小データ日などの定数を定義。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- なし（初回リリースのため該当なし）

### セキュリティ (Security)
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set を使用して既存 OS 環境変数を誤って上書きしないように実装）。
- OpenAI API キーは引数で注入可能（テスト時は環境変数に依存しない設計）。必須未設定時は明示的なエラーを返す。

### 注意事項 / 既知の制約 (Notes)
- OpenAI 連携機能は実際の API へのアクセスを前提としているため、実行には有効な `OPENAI_API_KEY` が必要。テストでは内部の `_call_openai_api` をモックすることを推奨。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となる。実行前にスキーマ準備を行ってください。
- research モジュールは外部ネットワークや注文機能を呼ばない設計（安全上の配慮）。
- 一部 DuckDB の executemany に関する互換性対策（空リスト不可等）を実装しているため、古い DuckDB バージョンでの動作確認が必要な場合があります。
- タイムゾーンは内部で UTC naive 日時を前提として扱う箇所があるため、DB に格納された日時が UTC であることを想定しています。

--- 

今後のリリースでは、ユニットテストの拡充、ドキュメント（API 使用例/DDL サンプル）、および運用向けの監視・ロギング改善を予定しています。