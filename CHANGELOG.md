CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

フォーマット:
- Unreleased: 今後の作業・既知の問題
- 0.1.0: 初回リリース（このコードベースのスナップショットから推測した機能一覧）

Unreleased
----------
注意・既知の問題および今後の改善候補（コード中の TODO / コメントから推測）

- 既知の不完全実装
  - kabusys.ai.news_nlp モジュールの score_news 実装が途中で切れている箇所があり、記事収集用の内部関数（例: _fetch_articles）や処理の末尾の書き込み処理が未表示／未実装と見受けられます。OpenAI 呼び出し周りのエラーハンドリングや DB への安全な部分置換ロジックは設計方針として記載されていますが、完全実装を確認してください。
- 改善候補 / 将来対応
  - portfolio.position_sizing: 銘柄ごとの lot_size をサポートする拡張（現状は全銘柄共通 lot_size を想定）。コメントに将来拡張の計画あり。
  - portfolio.risk_adjustment: price の欠損（0.0）に対するフォールバック（前日終値や取得原価など）の実装が未対応で、現状ではエクスポージャーが過少見積もられる可能性あり（TODO コメント）。
  - ai.news_nlp: 大規模バッチでの API 利用に伴うレート制御やバックオフ挙動は設計されているが、リトライ上限／ログとスループットの微調整が想定される。
  - utils.process_priority: 一部プラットフォームで権限不足により優先度設定が失敗するケースがあるため、運用手順書で権限要件を明確化することを推奨。

0.1.0 - 2026-04-16
------------------
初回リリース（このコードスナップショットに基づく主要な追加/機能一覧）

Added
- 基本パッケージ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を定義。

- 環境設定 / 管理
  - kabusys.config.Settings クラスを実装。
    - .env / .env.local の自動ロード機構（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env ファイルのパースは export 句のサポート、クォート文字・エスケープ、インラインコメント処理に対応。
    - 多数の設定プロパティを提供: J-Quants / kabu API / LINE / データベースパス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH) / 監視関連設定 (pid ファイル等) / CPU/Memory/Disk の閾値 / 環境種別 (development, paper_trading, live) / ログレベル検証など。
    - 必須環境変数未設定時には ValueError を投げる _require を提供。

- 実行系 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
    - BrokerClientFactory によりブローカークライアントを生成（Mock を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行（スレッド実行・停止フラグ監視・PID ファイル管理）。
    - RiskConfig に初期値を設定し、broker.get_available_cash() を初期ポートフォリオ値として使用。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（明示的な動作）。
    - プロセス起動時にプロセス優先度を "high" に設定する処理を実行。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループを終了。

- 監視 DB 初期化
  - run_* 側で init_monitoring_db を呼出し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - kabusys.utils.process_priority
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity によりカレントプロセスを先頭 N コアにピンする機能。
    - 権限不足や未対応プラットフォーム時には警告を出してフォールバックする実装。

- Portfolio 構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: buy シグナルを score 降順、signal_rank をタイブレークにして上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックして警告ログ。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 既存ポジションのセクター比率が上限を超える場合に当該セクターの新規候補を除外。unknown セクターは除外対象外として扱う。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じて投下資金乗数を返す（既定値: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 でフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based, equal, score) に応じて発注株数を計算。
    - リスクベース計算、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、lot_size 単位への丸め、cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト推定と再配分ロジックを実装。
    - aggregate cap スケーリングでは小数の端数を lot_size 単位で復元するための残差ソート手法を採用している（再現性確保のため code を二次キーに使用）。

- Research / ファクター計算・解析
  - kabusys.research.factor_research
    - calc_momentum: mom_1m/3m/6m と 200 日移動平均乖離 ma200_dev を計算（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR / 相対 ATR / 20 日平均売買代金 / 出来高比 を計算。true_range 計算は high/low/prev_close の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出（EPS が 0 または NULL の場合は None）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。引数 horizons の検証あり（1〜252）。
    - calc_ic / rank: スピアマンランク相関（IC）計算。records の join と None/非有限値の除外、3 レコード未満で None を返す安全処理。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- AI / ニュース NLP（OpenAI 統合設計）
  - kabusys.ai.news_nlp
    - raw_news を元に銘柄ごとのニュースを集約し、OpenAI の gpt-4o-mini（JSON Mode）でセンチメントを取得して ai_scores テーブルに書き戻す設計。
    - バッチ処理（1 回で最大 20 銘柄）、トークン肥大化対策（1 銘柄最大記事数/最大文字数でトリム）、JSON バリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどを想定。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - Score 生成は api_key パラメータまたは環境変数 OPENAI_API_KEY を参照（未設定時は ValueError）。
    - 設計文書・注釈により、API 失敗時に他銘柄スコアを保護するため部分置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）を行うことが意図されている（ただし完全実装はスナップショット上不完全）。

- CLI / ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを提供（コマンドライン実行モード: python -m kabusys.tools.paper_verification_report）。
    - 検証指標: 稼働率（uptime_pct）、注文成功率（fill_ratePct）、送信率（send_ratePct）、P95 レイテンシ、リスク却下数など。
    - デフォルト閾値: 稼働率 >= 99.0%、fill_rate >= 90.0%、send_rate >= 95.0%、P95 <= 200 ms。期間指定 (--from / --to) と DB パス指定 (--db) をサポート。
    - DuckDB/SQLite のテーブル欠如時には例外を吸収して空の結果として扱い、レポートを生成するフェイルセーフを持つ。

Changed
- （初回リリースに相当するため「Added」に集約）

Fixed
- （初回リリースのため特定の「修正」は無し）

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で与える必要があり、未設定時は ValueError を投げて安全性を確保。

Notes / 運用上の注意
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に留意すること（意図的な設計であれば問題なし、テスト環境で分離が必要な場合は設定変更）。
- process_priority/set_cpu_affinity は権限やプラットフォーム差により実行できない場合がある（警告ログが出力されフォールバックされる）。
- portfolio の計算は全て「純粋関数」設計（DB 参照なし）、テストが容易な実装になっている。
- DuckDB を利用したファクター計算は SQL による窓関数等を多用しており、大量データを扱う想定。クエリのパフォーマンス監視が必要。

Authors / Contributors（推測）
- コード中のコメントと設計方針から、金融アルゴリズムと運用監視を意識した開発者による実装。各モジュールは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に準拠している旨の注記あり。

ライセンス
- このスナップショットにはライセンス情報が含まれていません。実運用前にライセンスファイルの追加・確認を推奨します。

---
備考:
- 上記は提供されたソースコードの内容とコメントから推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してマージしてください。