Keep a Changelog
=================
すべての重要な変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

変更の粒度はコードベースから推測したものであり、実際のコミット履歴に基づくものではありません。

Unreleased
----------
- ドキュメント / TODO 更新
  - news_nlp モジュールの残り処理（_fetch_articles 等）が未完のため、OpenAI との完全な統合処理を完了する予定。
  - position_sizing の price 欠損時フォールバック（前日終値や取得原価を使う等）の実装検討。
  - DuckDB / SQLite への書き込み操作の部分的失敗時のリカバリやトランザクション保証について追加の堅牢化予定。
- テスト強化
  - エッジケース（環境変数の異常値、DB スキーマ不整合、API レスポンス異常）に対する単体テスト・統合テストを追加予定。

[0.1.0] - 2026-04-16
--------------------
追加 (Added)
- 全体
  - 初期リリースとして主要サブシステムを追加。
  - バージョン情報をパッケージルートに追加 (kabusys.__version__ = "0.1.0")。

- 設定・環境読み込み (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。OS 環境変数を保護しつつ上書き制御が可能。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート
    - コメント扱いの判定ロジックを改善（クォート外での # の扱い）
  - 環境値取得のユーティリティ (Settings クラス) を追加:
    - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
    - API トークン / シークレット取得（必須チェック）
    - Paper trading / production / development を識別する env ロジック（KABUSYS_ENV）
    - 監視閾値や PID パス等の各種設定をプロパティで提供
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクト data/stop_requested.flag を検知して安全終了。
    - 監視 DB は環境に依らず本番 sqlite_path を使用。
    - プロセス優先度を起動時に "high" に設定（utils.process_priority 経由）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - paper_trading モード時は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成を利用（テスト用 MockBroker を含む想定）。
    - Engine を別スレッドで実行し、停止フラグで安全停止できる仕組みを実装。
    - Execution 用 PID ファイルのパス管理（data/execution.pid）。

- 監視関連
  - monitoring.monitoring_db.init_monitoring_db 呼び出しで監視テーブルが存在することを保証（冪等）。

- ユーティリティ (kabusys.utils.process_priority)
  - クロスプラットフォームでのプロセス優先度設定を実装:
    - Windows: psutil の HIGH_PRIORITY_CLASS などを使用
    - POSIX (Linux, Darwin, FreeBSD): nice 値で設定
    - 許可エラーや未対応 OS はログ警告でスキップ
  - CPU affinity 設定ユーティリティを追加（指定コア数にプロセスをピンニング）。アクセス権限エラーを許容してフォールバック。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコアでソートして上位 N を返す。
    - calc_equal_weights, calc_score_weights: 等分配 / スコア加重配分を実装（スコア全ゼロ時は等分配へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックによる新規候補の除外ロジック。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポートし、lot_size（単元）丸め、per-stock 上限、aggregate cap（利用可能現金によるスケールダウン）、コストバッファ考慮のスケーリングを実装。
    - 利用可能現金を超えた場合のスケールダウンと残差処理（lot 単位での追加配分）を実装。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を組み合わせて PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損扱い・小サンプル時の None 処理）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージ __all__ に主要機能をエクスポート。

- ツール (kabusys.tools)
  - paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を集約して稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db をサポートし、日付ウィンドウの ISO8601 UTC 変換・DB 存在チェックを実装。
    - P95 の計算、閾値定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメント評価したスコアを ai_scores テーブルに書き込む設計を実装。
  - バッチサイズ、文字数制限、記事数上限、スコアの ±1.0 クリッピング、429/5xx 等に対する指数バックオフリトライ等の耐障害性を考慮。
  - ニュースウィンドウ計算（JST → UTC の変換）と API キー解決ロジックを実装。
  - （注）当バージョンのファイルは途中で切れており、記事取得部分や完全な書き込みロジックが未完。

変更 (Changed)
- DB ハンドリング
  - monitoring 用 init_monitoring_db を起動時に必ず呼び出すことで監視テーブルの存在を保証（冪等化）。
- Execution 側の DB 分離
  - paper_trading 環境時に paper_sqlite_path を用いて本番 DB と分離する方針を明示。

修正 (Fixed)
- .env 読み込みの堅牢性向上
  - ファイル読み込み失敗時に warnings.warn を使って通知し、例外を露出しないように変更。
- MONITOR_POLL_INTERVAL の不正値取り扱い
  - 0 以下や非整数が指定された場合はデフォルトにフォールバックし、警告ログを出力。

既知の問題 / 注意点
- position_sizing: price_map / open_prices に 0.0 や欠損があるとエクスポージャーが過少見積りされる可能性がある（将来的にフォールバック価格の導入を予定）。
- news_nlp: ファイル末尾が切れており、_fetch_articles 等の実装が未確認。OpenAI 連携部分は実験的実装のため、本番運用前にリトライ・エラーハンドリング・レスポンス検証を十分に評価すること。
- set_process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでは警告を出して処理をスキップする設計だが、想定外の環境で動作が制限される可能性あり。

セキュリティ (Security)
- 機密情報（API キー等）は Settings 経由で環境変数から取得する設計。リポジトリ内にハードコードしないよう留意。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途、CI/CD 等での安全対策）。

---
注: 上記の CHANGELOG は現行のソースコードから機能・設計意図を推測して作成したものであり、実際のコミット単位の履歴とは異なります。必要に応じて実コミットログやリリースノートに合わせて調整してください。