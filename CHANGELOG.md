# CHANGELOG

すべての重要な変更を Keep a Changelog のガイドラインに従って記録します。  
フォーマットや方針の詳細: https://keepachangelog.com/ja/1.0.0/

なお、本ログは提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- （現在未リリースの変更点はここに記載）

## [0.1.0] - 2026-03-28
初期公開リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 kabusys を追加。バージョンは 0.1.0。
  - 公開 API: kabusys.data / kabusys.research / kabusys.ai など主要モジュールを含むパッケージ構成を提供。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env パース機能を強化:
    - コメント行、export プレフィックス、クォート（' / "）およびバックスラッシュエスケープに対応。
    - クォートなしのインラインコメント検出ルールを実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定をプロパティで取得可能。
  - 設定値検証:
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の許容値チェック。
    - 必須値未設定時は ValueError を送出する _require() を実装。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いた一括（バッチ）センチメント評価を実装。
    - バッチサイズ、記事数・文字数上限などトークン肥大化対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ/バックオフ戦略：429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフで再試行。
    - レスポンスの厳密なバリデーションと ±1.0 でのクリップ。部分成功時は既存スコアを保護するため対象コードのみ置換（DELETE → INSERT の冪等処理）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をパッチ可）。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() として公開。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、結果の DuckDB への冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - LLM 呼び出しはニュースモジュールと独立した実装にしてモジュール間結合を低減。
    - ルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない設計。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を元にした営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB にデータがない日については曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得し冪等保存）。バックフィルや健全性チェックを実装。
  - ETL パイプライン (pipeline / etl)
    - ETLResult データクラスを追加し、ETL の取得数 / 保存数 / 品質問題 / エラー情報を集約可能に。
    - 差分取得、バックフィル、品質チェックの設計方針を反映（jquants_client と quality モジュール連携を想定）。
    - _get_max_date 等のヘルパーを実装し、DuckDB テーブル存在チェックや最大日付取得を提供。
  - jquants_client のラッパを想定した保存/取得処理との連携点を整備（インターフェース想定）。

- リサーチ（定量分析） (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER、ROE）、Liquidity などの定量ファクター計算関数を実装。
    - DuckDB 上の SQL＋窓関数で実行し、(date, code) をキーとする辞書リストで結果を返す設計。
    - データ不足時の None 処理、ログ出力を実装。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）による IC 計算。少数データや ties 対策を考慮。
  - データ系ユーティリティ（zscore_normalize）を再エクスポートして分析ワークフローを簡略化。

### 変更 (Changed)
- （初回リリースのため履歴的変更はなし。設計上の方針や互換性注記を各モジュールに明記）

### 修正 (Fixed)
- （初回リリースのため既知のバグ修正履歴はなし）

### 注意 / 設計上の注記 (Notable design / behavior)
- OpenAI 呼び出し
  - gpt-4o-mini を想定し JSON Mode を利用（厳密な JSON 出力を期待）。外部 API の不安定性に備えて堅牢なパース・バリデーションとリトライ戦略を実装。
  - テスト容易性のために内部の API 呼び出し関数をモック可能に分離。
- DB 書き込みは冪等性を重視（DELETE → INSERT のパターン、BEGIN/COMMIT/ROLLBACK を明示）。
- ルックアヘッドバイアス対策として、すべての分析/スコアリング関数は内部で現在時刻を参照せず、引数で与えた target_date の過去データのみを使用する設計。
- DuckDB 互換性のため一部の executemany 挙動やリストバインド回避ロジックを実装（空リストの executemany 回避など）。
- 環境変数ローダは既存 OS 環境を保護するため protected set を用いて上書き制御を実装。

### 既知の制約・未実装 (Known limitations)
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。
- News/Regime モジュールは OpenAI API キーを必要とする（api_key 引数か環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- 外部依存: DuckDB と OpenAI Python SDK を期待。外部 API（J-Quants / kabuステーション / Slack 等）との実運用連携は jquants_client や実行環境での設定を前提。

## セキュリティ (Security)
- 本リリースで特にセキュリティ修正は報告されていません。
- 注意点: 環境変数に API キー等の機密情報を保持する設計のため、.env 管理やアクセス権設定は運用上の注意が必要です。

---

作成した CHANGELOG.md はコードの実装内容から推測したものです。実際のリリースノート作成時はリリース日・変更者・マイグレーション手順等をプロジェクトの運用実態に合わせて適宜補足してください。