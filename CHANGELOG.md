CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。
語調は日本語です。

Unreleased
----------
- なし（この CHANGELOG は現状のコードベースから推測して生成されています）。今後の変更はここに記載します。

[0.1.0] - 初回リリース
---------------------
リリース日: (未指定)

Added
-----
- コアアプリケーション初期実装
  - パッケージ情報
    - kabusys.__version__ を "0.1.0" として定義。
  - 環境設定 / ロード
    - kabusys.config:
      - .env 自動読み込み機能（プロジェクトルートの .env / .env.local、OS 環境変数の保護機構）。
      - 複雑な .env パースの実装（export プレフィックス、シングル/ダブルクォート文字列、バックスラッシュエスケープ、インラインコメントの扱い）。
      - Settings クラスでアプリケーション全般の設定を提供（DB パス、Paper Trading 用パス、PID / kill フラグパス、各種閾値、ログレベル、環境判定メソッド等）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化オプション。
      - 必須環境変数未設定時に ValueError を送出する _require() 実装。

- 実行・監視エントリポイント
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を呼び出す。
    - 起動時にプロセス優先度を "high" にセット（set_process_priority）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様（明示的に分離されていないことに注意）。
    - 起動時にプロセス優先度を "high" にセット。

- ユーティリティ
  - kabusys.utils.process_priority:
    - Windows（psutil の priority class）と POSIX 系（nice 値）を吸収してプロセス優先度を設定する set_process_priority。
    - CPU コア数を制限する set_cpu_affinity を提供（引数検証・権限不足や未実装 API のフォールバック処理あり）。
    - 失敗時は警告ログを出して処理をスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順 & signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: スコア加重・等金額配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中（max_sector_pct）を評価して候補を除外。sell_codes を除外して当日売却予定銘柄を考慮。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知値は警告の上 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に従って株数を計算。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的コスト見積。
    - aggregate スケーリング後の端数処理を残差に基づき安定的に配分。

- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最終財務データを取得して PER / ROE を計算。prices_daily と結合。
    - 各関数はデータ不足時に None を返す安全な設計。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使った一括取得）。horizons の検証あり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。レコード数が少ない場合は None。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- AI ニュース NLP（OpenAI 連携）
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI (gpt-4o-mini) にバッチ送信して銘柄別センチメントスコア（-1.0〜1.0）を ai_scores に書き込む処理を実装。
    - ニュース収集ウィンドウの明確化（JST 基準で前日 15:00 ～ 当日 08:30、UTC 変換実装）。
    - バッチサイズ、最大記事数・文字数制限、スコアクリッピング、最大リトライ等の定数パラメータを提供。
    - API の 429/ネットワーク/5xx 等に対する指数バックオフリトライ、レスポンスバリデーション、部分成功時の DB 書き換え戦略（対象コードを限定して DELETE → INSERT）などフェイルセーフ実装。
    - API キー未設定時に ValueError を送出。

- 検証ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し CLI レポート出力。
    - 日付フィルタ (--from / --to)、--db オプションを提供。DB が存在しない場合やテーブル欠如時の扱いを明示。
    - P95 計算、数値フォーマット、閾値による PASS/FAIL 判定を実装。

Changed
-------
- 設定 / 検証の強化
  - Settings.env / log_level / paper_fill_mode などで不正値に対して ValueError を返すように検証を追加。
  - .env ローダーは OS 環境変数を保護する protected 機能を追加（.env.local の override が存在しても OS 環境変数は上書きされない）。

- 実行フローの安全化
  - run_monitoring.run() のポーリングループ内で monitor.check_once() の例外を捕捉してロギングし、次のポーリングまで継続するフォールバックを追加。
  - run_execution / run_monitoring で起動直後にプロセス優先度を上げる処理を共通化（set_process_priority の利用）。

Fixed
-----
- フォールバック / エラーハンドリングの改善
  - MONITOR_POLL_INTERVAL のパースで 0 以下の値や非整数を検出した場合にデフォルト（60 秒）に戻すようにし、警告ログを出すようにした（run_monitoring._get_poll_interval）。
  - calc_score_weights: 全銘柄のスコア合計が 0.0 の場合は等金額配分にフォールバックし、WARNING を出すように修正。
  - portfolio.position_sizing:
    - 価格欠損や price <= 0 のケースをスキップすることで ZeroDivision や不正な計算を回避。
    - lot_size 単位で切り捨て／追加配分を行う際の端数処理と aggregate cap スケーリングで一貫性を確保。
  - research モジュール:
    - データ不足や NULL 値に対して None を返すなど、NaN/NULL 伝播に配慮した実装に修正。
    - calc_forward_returns の horizons 引数検証を追加（正の整数で 252 以下）。
  - process_priority: サポートされない OS や権限不足時に例外を握り潰して警告ログでスキップするようにした。

Security
--------
- API キーの取り扱い
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的にエラーにして処理を止める設計（誤った公開の軽減）。

Known issues / Notes
--------------------
- Monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様になっています。paper_trading 環境で監視を別 DB にしたい場合は設定を見直す必要があります。
- position_sizing の価格フォールバック（price が欠損時の扱い）は TODO コメントが残っており、前日終値や取得原価を用いたフォールバックの検討が必要です。
- news_nlp モジュールは OpenAI へのネットワーク依存があり、API 呼び出しのコストやレート制限により部分失敗があり得ます。部分失敗時でも既存のスコアを保護する設計になっていますが、運用ルールの整備を推奨します。
- DuckDB に関して executemany の制約やバージョン依存の注意点がいくつかコメントに記載されています（注意して運用してください）。

Credits
-------
- コードベースから自動推測して作成した CHANGELOG です。実際のコミット履歴に基づく正式な CHANGELOG を作成する場合は git log 等の履歴情報を使用してください。