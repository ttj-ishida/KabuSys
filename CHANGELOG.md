# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開 API:
    - src/kabusys/__init__.py で主要サブパッケージを公開: data, strategy, execution, monitoring
  - 環境設定 / 起動時自動 .env 読み込み:
    - src/kabusys/config.py
      - プロジェクトルートを .git / pyproject.toml から探索して自動で .env / .env.local を読み込む機能を提供
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
      - export KEY=val, クォートやエスケープ、行内コメントのパースに対応する堅牢な .env パーサを実装
      - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス /実行環境（development/paper_trading/live）などの設定を明示的に取得可能
      - LOG_LEVEL / KABUSYS_ENV の妥当性チェック（想定値以外は ValueError）
  - AI（自然言語処理）モジュール:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメント（ai_score）を算出する機能を提供（score_news）
      - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり最大記事数と文字数でトリム、レスポンス検証、スコアクリッピング（±1.0）
      - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。API 失敗時は個別チャンクをスキップして継続（フェイルセーフ）
      - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（モジュール内の _call_openai_api を patch で置換）
      - calc_news_window: JST ベースのニュース集計ウィンドウ計算ユーティリティを提供（前日15:00～当日08:30 JST に対応）
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を提供（score_regime）
      - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）、リトライ／エラーフォールバック（失敗時 macro_sentiment=0.0）
      - レジームスコア合成ロジック、閾値に基づくラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
  - Research（リサーチ）モジュール:
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算を提供（calc_momentum, calc_volatility, calc_value）
      - DuckDB SQL を活用した効率的な集計実装。データ不足時は None を返す挙動
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、Information Coefficient（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）等を実装
    - zscore 正規化ユーティリティを data.stats から再エクスポート
  - Data プラットフォーム:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）および夜間バッチ更新 job（calendar_update_job）を実装
      - market_calendar が未登録の場合は曜日ベースのフォールバックを使用する設計
      - カレンダー取得は J-Quants クライアント経由（jquants_client を利用）
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETL パイプラインのインターフェースと結果データ構造（ETLResult）を提供
      - 差分更新、backfill、品質チェック（quality モジュールとの連携）を想定した設計
      - ETLResult は品質問題やエラー情報を保持し、辞書化（to_dict）可能
    - DuckDB をメインのローカル DB と想定（デフォルトパス: data/kabusys.duckdb、監視用 sqlite デフォルト: data/monitoring.db）
  - 設計方針（ドキュメント化）
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない（多くの関数が target_date 引数を受ける）
    - DB 書き込みは冪等性を考慮（既存行の削除→挿入や ON CONFLICT 方針を想定）
    - API 呼び出しは保守性/テストを考慮して差し替え可能に実装

### Changed
- 初回リリースのため該当なし（設計上の注意点・デフォルト値などを明記）
  - OpenAI モデル選定: gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で利用する設計を採用
  - バッチ・スキャン・ウィンドウ等のデフォルトパラメータを明文化（例: ニュース集計ウィンドウ、バッチサイズ、MA 窓など）

### Fixed / Robustness
- エラー時のフォールバックを明確化
  - news_nlp / regime_detector の OpenAI 呼び出しで API エラー・パースエラーが発生した場合、例外をそのまま上げずに該当処理はスキップまたはゼロ値で継続する実装（ロバストなフェイルセーフ）
- DuckDB の executemany に関する互換性対応
  - 空リストでの executemany 呼び出しを避ける条件分岐を追加（DuckDB バージョン差異への対処）
- API リトライロジックに指数バックオフと最大試行回数を導入（設定定数化: _MAX_RETRIES, _RETRY_BASE_SECONDS）

### Internal / Other
- モジュール境界・テスト容易性を重視
  - OpenAI への実際の呼び出しは _call_openai_api として分離し、テストでモック可能に実装
  - レスポンスパース処理は堅牢に実装（余分な前後テキストが混入した JSON でも復元を試みる）
- ロギング強化
  - 各主要処理に INFO/DEBUG/WARNING/EXCEPTION ログを追加し、処理状況と異常時の原因追跡を容易に

---

注記:
- 本リリースは「機能追加の初期版」を目的としており、外部 API（OpenAI, J-Quants, kabu API 等）との実運用連携に際しては各種 API キーや構成（.env の作成）が必要です。
- 実環境（live）での発注等を行うモジュール（strategy / execution 等）はパッケージ中で名前空間として公開されていますが、発注ロジック・安全性ガードは運用ポリシーに応じて追加・確認してください。