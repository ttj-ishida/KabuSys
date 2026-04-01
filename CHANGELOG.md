CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」準拠の形式で記載しています。バージョン運用方針はセマンティックバージョニングに従います。

[Unreleased]
-------------

（現在未リリースの変更はここに記載します。）

0.1.0 - 2026-04-01
------------------

初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージトップレベルで version = 0.1.0 を設定。
  - パッケージの公開 API を __all__ で定義（"data", "strategy", "execution", "monitoring"）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、インラインコメント処理など。
    - override / protected オプションにより OS 環境変数の保護や .env.local による上書きを実現。
  - 必須設定取得用の _require() と、いくつかの既定値（KABU_API_BASE_URL、データベースパス等）を提供。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証。

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントスコアを ai_scores テーブルへ書き込む機能を実装（score_news）。
    - タイムウィンドウ定義（前日15:00 JST〜当日08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大20銘柄／リクエスト）、1銘柄あたり記事上限・文字数トリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API 呼出し失敗時のフェイルセーフ（失敗はスキップして継続）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定（score_regime）。
    - prices_daily/raw_news を利用したデータ取得、calc_news_window を利用したウィンドウ処理。
    - OpenAI 呼び出し（gpt-4o-mini）のリトライ/エラー処理、API失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。

- データパイプライン（kabusys.data）
  - ETL 結果を表す ETLResult データクラスを導入（kabusys.data.pipeline → kabusys.data.etl で再エクスポート）。
    - ETL の取得数・保存数・品質問題リスト・エラー一覧を保持。has_errors / has_quality_errors 等のユーティリティを提供。
  - ETL パイプライン（kabusys.data.pipeline）:
    - 差分取得、バックフィル、品質チェックのための基盤コードを整備。
    - jquants_client 経由の idempotent 保存（ON CONFLICT 相当）と品質検査（kabusys.data.quality の利用）を想定。
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX マーケットカレンダーの夜間更新ジョブ（calendar_update_job）を実装。バックフィル、健全性チェック、J-Quants からの差分取得・保存をサポート。
    - 営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。DB にデータが無い場合は曜日ベースのフォールバックを採用。
    - 最大探索範囲や再取得期間などの安全策を実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER/ROE）、Volatility（20日ATR）、Liquidity（20日平均売買代金、出来高比）を DuckDB の SQL と Python を組合せて計算する関数群を実装（calc_momentum / calc_value / calc_volatility）。
    - データ不足時の None 返却、結果は (date, code) をキーとする dict のリストで返す。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。スピアマン相関（ランク相関）をランク変換と Pearson 相関計算で実装。

- 共通設計方針・品質
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主要なストレージ層として使用。SQL と純粋 Python の組合せにより処理を実装。
  - DB への書き込みは可能な限り冪等性を確保（DELETE→INSERT や ON CONFLICT 相当の保存を想定）。
  - OpenAI 呼び出しは JSON Mode を活用し、レスポンスの堅牢な検証を実装。テスト用に _call_openai_api を差し替え可能。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Removed
- （初期リリースにつき該当なし）

Security
- （現時点で特記すべきセキュリティ修正はなし）
  - 注意: OpenAI API キーや各種トークンは環境変数で管理すること。Settings._require は未設定時に ValueError を送出します。

開発者向けメモ
- OpenAI 呼び出しのテスト:
  - news_nlp と regime_detector の両モジュールで _call_openai_api を unittest.mock.patch により差し替えることで外部 API 依存を排除して単体テスト可能。
- 環境変数の自動ロード:
  - パッケージ import 時にプロジェクトルートが検出されると .env / .env.local を自動で読み込みます。テストでこれを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB executemany の注意:
  - DuckDB 0.10 系では executemany に空リストを渡すとエラーとなるため、空チェックを行った上で executemany を呼び出しています。

ライセンス・依存
- OpenAI Python SDK（Chat Completions / JSON Mode）を利用する想定。利用する際は該当 SDK のバージョン互換性に注意してください。
- DuckDB をデータ層に使用。

今後の TODO（例）
- strategy / execution / monitoring モジュールの実装（現在はパッケージ公開のみ）。
- ai モジュールの追加評価指標（コンフィデンス推定など）。
- より高度な品質チェックルールの実装とアラート統合。

--- 

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は実コミット履歴やリリース管理ポリシーに合わせて調整してください。）