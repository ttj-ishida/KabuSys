# Changelog

すべての変更は Keep a Changelog の方針に従い、重要な変更点を分類して記載しています。  
日付は本コードベースのスナップショット（コード内の実装に基づき推測）を基準に付与しています。

## [Unreleased]
### Added
- 実行/監視起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するスクリプト。環境変数 KABUSYS_ENV に応じて paper_trading モードでは専用の SQLite DB（data/paper_trading.db など）と MockBroker を利用する。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- AI 関連機能を追加
  - kabusys.ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント（ai_score）を算出し、ai_scores テーブルへ書き込む処理を実装。バッチ化・トリム・再試行・レスポンス検証・スコアクリッピング（±1.0）を行う。
  - kabusys.ai.regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して日次の market_regime を判定・書き込みするモジュールを追加。API エラー時のフェイルセーフや冪等書き込みを考慮。
- リサーチ・ファクター分析機能を追加
  - kabusys.research.factor_research: momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）を実装。MA200 や ATR 等の計算を SQL＋Python で行う。
  - kabusys.research.feature_exploration: 将来リターン計算（horizons 対応）、IC（Spearman）計算、ファクター統計要約、ランク化ユーティリティを追加。
- ポートフォリオ構築関連の純粋関数を追加
  - kabusys.portfolio.portfolio_builder: 候補選定（スコア降順）、等金額配分 / スコア加重配分の実装（スコア全て 0.0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジームの既定値を明示。
  - kabusys.portfolio.position_sizing: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン（端数の再分配ロジック含む）などの細かい制約を実装。
- 設定 / 環境読み込みを強化
  - kabusys.config: .env / .env.local の自動ロード機能を導入（OS 環境変数優先、.env.local が .env を上書き）。export 前置、クォート、インラインコメント等のパースに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 環境変数アクセス用 Settings クラスを実装し、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）で未設定時に ValueError を送出する安全機構を追加。PAPER_FILL_MODE 等の検証も行う。
- プロセス制御ユーティリティを追加
  - kabusys.utils.process_priority: プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定する機能を追加。Windows / POSIX の差異に対応し、例外時は警告でスキップ。CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。

### Changed
- パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定（初期バージョン）。
- DB 接続ポリシー明示
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（monitoring.db）を使用する方針を明記（監視用データは本番 DB を参照）。

### Fixed
- DuckDB への書き込み安全性の考慮
  - DuckDB 0.10 の executemany に空リストを渡すと失敗する制約を回避するため、書き込み前に params が空でないことをチェックしてから executemany を呼び出すようにした（news_nlp の書き込み処理等）。
- OpenAI API 呼び出しの堅牢化
  - rate limit / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライする実装を追加。想定外のレスポンスは警告ログを出して該当チャンクをスキップするフェイルセーフを導入。

### Security
- API キーの取り扱い
  - OpenAI API は明示的に api_key 引数または環境変数 OPENAI_API_KEY で供給する必要があることを明記。未設定時は ValueError を送出して早期検出する。

## [0.1.0] - 2026-04-11
最初の公開リリース想定のまとめ（上記の主要機能を含む）。

### Added
- 上記 Unreleased の全機能をこの初版に含めてリリース：
  - 実行エンジン & 監視ループ起動スクリプト
  - AI ニュース NLP（銘柄センチメント算出）
  - 市場レジーム判定モジュール
  - リサーチ・ファクター計算（モメンタム／ボラティリティ／バリュー）・IC 計算・統計サマリー
  - ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制限・レジーム乗数）
  - 環境設定管理（.env 読み込み、Settings クラス）
  - プロセス優先度 / CPU affinity ユーティリティ
  - DuckDB / SQLite を用いたデータ入出力の基盤ロジック

### Changed
- モジュール設計の方針・ルールを明記
  - ルックアヘッドバイアス防止のため、AI / レジーム判定 / ニュース処理は date 引数を受け取り、datetime.today() / date.today() を参照しない設計を採用。
  - DuckDB 上のクエリは可能な限りウィンドウを限定してパフォーマンスを考慮。

### Fixed
- 各種入出力・例外ハンドリング強化（詳細は上記）。

## 既知の注意点 / マイグレーションノート
- 環境変数の必須チェック
  - Settings の一部プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError を投げます。デプロイ時は .env を適切に設定してください（.env.example を参照）。
- MONITOR_POLL_INTERVAL
  - run_monitoring で MONITOR_POLL_INTERVAL を 0 や負の値に設定すると無効としてデフォルト（60 秒）にフォールバックします。
- 監視 DB の利用ポリシー
  - 監視プロセスは環境に依らず本番 sqlite_path を使用します。テスト・paper_trading と監視を完全に分離したい場合は運用ルールで対処してください。
- OpenAI 呼び出しは外部 API 依存
  - news_nlp / regime_detector は OpenAI API キーとネットワークアクセスが必要です。API 利用量・レート制限に注意してください。API エラー時はフェイルセーフ（部分スキップ・デフォルト値）で継続する設計です。
- DuckDB executemany の互換性
  - DuckDB バージョンによっては空の executemany が失敗するため、書き込みパラメータが空でないことを明示的にチェックしています。

もしリリースノートをバージョン分割（例: 0.1.0 → 0.1.1 のように細かく分ける）したい場合や、各モジュールごとの変更点（関数仕様・引数・戻り値の詳細）を追記したい場合は、その粒度での履歴を生成します。どの程度の詳細が必要か教えてください。