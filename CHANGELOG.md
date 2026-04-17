# Changelog

全ての注目すべき変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更（未リリース）
- 各リリースは日付付きで記載

なお、以下の内容は提供されたコードベースから推測して作成しています。

## [Unreleased]

### 注意事項
- ai/news_nlp.py が途中で切れており（_fetch_articles 等の実装が欠落、処理が不完全）、この部分は開発継続・要完成です。
- position_sizing や risk_adjustment 内に将来的な拡張を示す TODO コメントがあります（例: 銘柄別 lot_size、価格フォールバックの実装検討）。
- 実行環境によってはプロセス優先度・CPU affinity の設定が権限不足で失敗する可能性がある旨のハンドリング（警告出力）は入っているものの、運用手順に注意が必要です。

---

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB (data/paper_trading.db デフォルト) と MockBrokerClient を使用し、本番 DB と分離。
    - 起動前に停止フラグを確認し、エンジンは別スレッドで実行。停止フラグ検知で安全停止。
    - PID ファイルの取り扱い（data/execution.pid）。

- 設定管理
  - config.py
    - .env/.env.local の自動ロード（OS 環境変数優先、.env.local は上書き可能）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース機能強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理。
    - Settings クラスを導入し、環境依存の設定値（DB パス、API トークン、PID/FLAG パス、監視閾値、ログレベル、env 判定など）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
    - env 値の検証（development/paper_trading/live）とログレベル検証。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成コマンドラインツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - 日付フィルタ (--from, --to) と DB パス指定 (--db) に対応。
    - P95 計算実装、しきい値はソース内で定義（稼働率 99%、成立率 90% 等）。

- ポートフォリオ構築（純粹関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア全て 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有を考慮して新規候補の除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告のうえ 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 株数決定ロジック。allocation_method による "risk_based" / "equal" / "score" 対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用現金に合わせたスケールダウン）、cost_buffer による保守的見積もり、残差を lot 単位で再配分するロジックを実装。
    - 将来的な拡張（銘柄別 lot_map、価格フォールバック）について TODO コメントあり。

- 研究・リサーチ
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクターの計算関数を追加（DuckDB を用いて prices_daily / raw_financials を参照）。
    - 200日移動平均、ATR20、平均売買代金、各種モメンタム（1m/3m/6m）を計算。
  - research/feature_exploration.py
    - 将来リターン（複数ホライズン）計算、IC（Spearman ランク相関）計算、ファクター統計サマリ（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py で関連機能をエクスポート。

- AI / NLP（ニューススコアリング）
  - ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む設計を追加。
    - 処理フロー: ニュースウィンドウ計算、記事トリミング（最大記事数・最大文字数）、バッチ送信（最大 20 銘柄）、リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ、部分置換による安全な書込（DELETE→INSERT）を想定。
    - API キーの指定/環境変数参照対応、タイムウィンドウ計算ユーティリティ calc_news_window を提供。
    - 注意: ファイル末尾が切れており実装未完（_fetch_articles の呼び出し以降が未完）。

- ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX の差分を吸収する set_process_priority（high/normal/low）。
    - set_cpu_affinity によるプロセスの CPU コア固定機能。
    - 権限不足や未対応環境での例外は警告に変換して安全にスキップする実装。

- パッケージメタ
  - __init__.py にてパッケージ名と __version__ = "0.1.0" を定義。

### 変更 (Changed)
- .env 読み込みの優先度と上書きルールを明確化（OS 環境変数 > .env.local > .env、.env.local は上書き許可）。
- Settings のプロパティによる集中管理により、各モジュールで直接 os.environ を参照する必要を軽減。

### 修正 (Fixed)
- .env のパースを堅牢化（クォート・エスケープ・コメント処理の改善）し、実運用での .env 設定ミス耐性を向上。
- run_execution/run_monitoring が DB を開く際に monitoring テーブル等を冪等に初期化する処理を追加（init_monitoring_db 呼び出し）。

### 注意 (Notes)
- Paper Trading と Live の DB を明確に分離（paper_trading 環境では paper_sqlite_path を使用）することで、本番データと検証データの混在を防止。
- MONITOR_POLL_INTERVAL が 0 や負の値、非整数の場合はデフォルト（60秒）にフォールバックする安全策を実装。
- ai/news_nlp の未実装部分はリスク（レポート生成や自動スコアリングが期待通り動かない）を残すため、実運用前に完成とテストが必要。

### セキュリティ (Security)
- 外部 API キー（OpenAI・J-Quants・Kabu API など）は環境変数経由で取得し、明示的な未設定チェックを行う（未設定時は ValueError を送出する箇所あり）。キーの取り扱いに注意。

---

開発者向けの補足やマイグレーションポイントが必要であれば追記します。どのリリースノートを優先的に詳述するか（例: ai/news_nlp の完成予定、position_sizing の拡張等）を指示いただければ、その箇所を拡張して更新版 CHANGELOG を作成します。