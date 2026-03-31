# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成した初期リリースの変更履歴です。

今後の変更はトップに Unreleased を追加し、リリースごとに下に追記してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回公開リリース。本リリースではデータ取得・ETL・カレンダー管理・ファクター計算・AIによるニュースおよび市場レジーム判定等、分析／研究基盤と自動化ジョブのコア機能を実装しました。

### Added
- パッケージ基盤
  - パッケージ初期化ファイルを追加（kabusys.__init__）。モジュール公開: data, strategy, execution, monitoring（監視モジュールは将来的に追加予定）。
  - バージョン情報: 0.1.0 を設定。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 複雑な .env パース処理を実装（export プレフィックス、シングル・ダブルクォートのエスケープ、行内コメント処理など）。
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - Settings クラスを実装し、J-Quants、kabuステーション、Slack、DBパス、監視閾値、環境・ログレベル判定ユーティリティを提供。必須環境変数未設定時は詳細な ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄別センチメントを取得して ai_scores テーブルへ書き込む機能を追加。
    - バッチ処理（最大 20 銘柄／リクエスト）、記事トリム（最大記事数・最大文字数）、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ実装。
    - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフとリトライを実装。失敗時は該当チャンクをスキップして他は継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api を内部で分離（unittest.mock.patch で差し替え可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF（コード 1321）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次の市場レジーム（bull/neutral/bear）を market_regime テーブルへ冪等書き込みする機能を追加。
    - マクロニュースの抽出（マクロキーワードによるフィルタ）と OpenAI による JSON レスポンスパースを実装。API エラーやパース失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - LLM 呼び出しは専用関数で実装し、news_nlp と独立させることでモジュール結合を抑制。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを追加し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返却する仕組みを提供。
    - 差分更新、バックフィル、品質チェックの設計方針を反映（J-Quants クライアント経由で差分取得・idempotent 保存）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得などのユーティリティを実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した扱いを提供。
    - calendar_update_job を実装し、J-Quants から差分取得して冪等に保存（バックフィル・健全性チェックあり）。

- 研究・ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - momentum（1M/3M/6M リターン、ma200 偏差）、volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、value（PER、ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理やログ出力を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）を実装（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient、Spearman ρ）計算の実装（calc_ic）。
    - 値のランク変換（rank）とファクター統計サマリー（factor_summary）を実装。
  - kabusys.research.__init__ で主要関数をエクスポートし、zscore_normalize を data.stats から再エクスポート。

### Fixed / Robustness improvements
- 環境変数パースの堅牢化
  - .env のクォート・エスケープ・コメント処理を強化し、実運用での .env 記述ばらつきに耐えるように実装。
  - 自動ロード時に OS 環境変数を保護する設計を追加（.env.local の上書き制御含む）。

- OpenAI API 呼び出しの堅牢性向上
  - 429 / ネットワークエラー / タイムアウト / サーバー 5xx を対象に指数バックオフとリトライを導入（news_nlp と regime_detector 両方で実装）。
  - API レスポンスの JSON パース失敗や不正フォーマットに対するフォールバック（パース失敗時はスコアを 0.0 または該当チャンクをスキップ）を実装し、ジョブ全体が中断しないようにした。

- DuckDB 書き込みの冪等性と互換性
  - market_regime / ai_scores 等への書き込みを DELETE→INSERT のパターンで冪等化。
  - DuckDB executemany の実装差異に配慮して、空パラメータ時の挙動を回避するガードを追加。

### Documentation / Design notes
- 各モジュールに設計方針・処理フロー・注意点をドキュメント文字列として記載（ルックアヘッドバイアス回避のため date.today()/datetime.today() を参照しない方針等）。
- テスト容易化のために外部 API 呼び出し箇所（_call_openai_api 等）を差し替え可能に設計。

### Known limitations / TODO
- 監視関連モジュール（monitoring）は __all__ に含まれるが実装ファイルは未提供。今後追加予定。
- 一部の外部クライアント（jquants_client 等）の具象実装はここに含まれておらず、実行環境では別途クライアント実装が必要。
- 現行バージョンでは PBR・配当利回りなどの追加バリューファクターが未実装。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）を必須とするため、適切な環境設定が必要。

### Security
- 環境変数管理時に OS 環境変数を保護する仕組みを導入（.env による上書き制御）。機密情報の取り扱いについては運用ポリシーに従ってください。

---

（注）本 CHANGELOG はリポジトリ内のコードから推測して作成しています。リリースノートとして正式に公開する際は、実際のコミット履歴・リリース手順・テスト結果に基づいた追記・修正を行ってください。