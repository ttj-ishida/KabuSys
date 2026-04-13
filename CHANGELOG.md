# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース履歴はコードベースの内容から推測して作成しています。

## [Unreleased]

（該当なし）

## [0.1.0] - 2026-04-13

Added
- 基本パッケージ情報を追加
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 実行用エントリポイントを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine.run_session の呼び出し。
    - 起動時にプロセス優先度を設定（utils.process_priority）。
    - duckdb と sqlite3 の接続管理、終了時のクローズを確実に実行。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視用 DB は環境に関係なく本番 sqlite_path を使用。
    - 起動時にプロセス優先度を設定、pid ファイルを使用。
- 設定・環境読み込み機能を整備
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。.env と .env.local の優先度を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env 行パーサの実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
    - Settings クラスを導入し、各種設定値のプロパティ（DB パス、PID/KILL フラグ、閾値、env/log level 等）を提供。
    - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェック）。
- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db を run スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。
- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - paper_trading の SQLite DB（デフォルト data/paper_trading.db）を解析して検証レポートを生成する CLI。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）などを算出し閾値判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、DB パス指定 (--db / 環境変数) をサポート。
    - DB がない・テーブルがない場合の堅牢なフォールバック処理。
- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（score 降順、同点は signal_rank 昇順でタイブレーク）。
    - 等配分およびスコア加重配分ユーティリティ（全銘柄スコアがゼロの場合は等配分にフォールバックし警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限: apply_sector_cap（既存保有を元にセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外）。
    - レジームに基づく乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームは警告してフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position size 計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・投下資金上限、cost_buffer による保守的見積り。
    - aggregate cap 超過時のスケーリングと端数配分アルゴリズム（残余キャッシュで lot 単位の追加配分、再現性確保のためのソート安定化）。
- 研究・ファクター計算モジュール（DuckDB ベース）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）計算。
    - ボラティリティ（ATR20、相対 ATR、20日平均売買代金、出来高比）計算。
    - バリュー（PER, ROE）計算（raw_financials の最新レコード取得を含む）。
    - DuckDB のウィンドウ関数と効率的なスキャン範囲指定を利用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン（複数ホライズン）計算、IC（Spearman ρ）計算、rank（同位は平均ランク）、統計サマリーの実装。
    - pandas など外部ライブラリに依存せず標準ライブラリで実装。
- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を銘柄ごとに集約、OpenAI（gpt-4o-mini + JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - バッチサイズ、記事数・文字数上限（トークン肥大化対策）を設定。
    - API リトライ（429 / ネットワーク / 5xx）を指数バックオフで実行、レスポンスバリデーション、スコアを ±1.0 にクリップ。
    - スコア書き込みは部分失敗に強く、対象コードのみを DELETE→INSERT で更新（他コードの保護）。
    - API キー未設定時は ValueError を送出。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - マルチプラットフォーム対応のプロセス優先度設定（Windows / POSIX 系の差分吸収）。
    - CPU affinity 設定ユーティリティ（最初の N コアにピン留め）。
    - 権限不足や未サポート環境でのフォールバック（警告）を実装。

Changed
- 環境変数の読み込み順序と保護ロジック
  - OS 環境変数 > .env.local > .env の優先順位を明示。
  - .env 読み込み時に OS 環境変数を protected として上書きを防止。
- run_monitoring/run_execution の DB 接続ロジック整理
  - monitoring は常に本番 sqlite_path を参照する（環境に依存せず監視データを本番 DB に集約）。
  - execution は paper_trading 環境時に paper_sqlite_path を使用して完全に分離。

Fixed / Robustness
- .env パーサの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応し、より現実的な .env ファイルを正しく解析するよう改善。
- Settings の妥当性検証を追加
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等について不正値で早期に例外を投げることで、誤設定を起動時に検出可能に。
- ポートフォリオ/ポジション計算の堅牢化
  - 価格欠損（0 や None）や portfolio_value <= 0 の場合にスキップするなどのガードを追加。
  - スケーリングで生じうる端数処理の安定化（lot 単位での丸め、再現性のための安定ソート）。
- research / reporting の堅牢化
  - DuckDB クエリ結果が存在しない場合のフォールバック（None / N/A 表示）を実装し、テーブル未作成やデータ欠損時にもツールがクラッシュしないようにした。
- process_priority / cpu_affinity の権限エラーに対するフォールバックログ出力を追加。

Internal
- コードドキュメントと設計注記を充実
  - 各モジュールに設計方針、参考ドキュメント参照、注意事項（例: レジーム周り、将来拡張ポイント）を明記。
- モジュールのエクスポート整理
  - src/kabusys/portfolio/__init__.py、src/kabusys/research/__init__.py などで外部 API を明示的にエクスポート。

Security
- （該当なし）

Notes / 今後の改善予定（コード内コメントより）
- position_sizing:
  - lot_size を銘柄毎に持たせる設計への拡張を検討中。
  - price 欠損時のフォールバック価格（前日終値や取得原価）導入の検討。
- news_nlp:
  - 部分失敗時の更なる再試行ポリシーや永続化戦略の改善。
- モニタリング:
  - poll interval の runtime 設定 reconfigure や、より詳細なメトリクス収集の追加検討。

---
（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートはリリース手順・変更履歴管理に基づき調整してください。