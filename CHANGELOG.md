Keep a Changelog準拠（日本語）

すべての変更は意味的にコードベースから推測して記載しています。初回リリース（0.1.0）としてまとめています。

Unreleased
- なし

[0.1.0] - 2026-04-09
Added
- 全体
  - パッケージ初期リリース。バージョン __version__ = 0.1.0 を設定。
  - パッケージ公開用の主要モジュールを実装・エクスポート（data, strategy, execution, monitoring 等を __all__ に定義）。

- 環境設定 (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない動作を実現。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い等に対応）。
  - Settings クラスを追加し、アプリケーション設定値をプロパティ経由で取得可能に：
    - 必須値取得のための _require（未設定時は ValueError）
    - J-Quants / kabuステーション / LINE / DB パス / Paper Trading 用設定 / 監視閾値 / ログレベル等のプロパティ
    - 値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の有効値チェック）とデフォルト値の提供

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークに signal_rank を使用）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック、WARNING ログ出力）
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター別時価を計算し、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート。未知レジームは 1.0 でフォールバック）
  - position_sizing:
    - calc_position_sizes: 発注株数計算（allocation_method に "risk_based" / "equal" / "score" をサポート）
      - risk_based: 許容リスク率 risk_pct と損切り率 stop_loss_pct に基づく株数算出
      - equal/score: 配分重みと利用可能現金に基づく算出
      - lot_size（単元）対応、max_position_pct（銘柄毎上限）、max_utilization（投下資金上限）、cost_buffer（手数料/スリッページ見積り）を考慮
      - aggregate cap を超えた場合のスケーリングと、余り（fractional remainder）に基づく追加配分ロジックを実装（安定ソートによる再現性保持）
      - price 欠損時はスキップし、ログ出力で通知

- リサーチ / 特徴量 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率（MA200）計算（DuckDB の prices_daily を利用）
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（prices_daily と組合せ）
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括 SQL で取得（入力の妥当性検査あり）
    - calc_ic: スピアマンランク相関（IC）計算（None 値・非有限値の除外、レコード数が 3 未満なら None を返す）
    - rank: 同順位は平均ランクを返す（丸めによる tie 検出漏れ対策あり）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算
  - 外部ライブラリに依存せず DuckDB 接続のみで動作する設計（pandas 非依存）

- AI（OpenAI 経由の NLP）(kabusys.ai)
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに LLM（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み
      - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う）
      - 記事結合・文字数トリム（1 銘柄あたり最大記事数・文字数の制限）
      - バッチ処理（最大 20 銘柄 / API コール）
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 型チェック、コード照合、スコア数値化、±1.0 でクリップ）
      - 部分失敗時に既存スコアを保護するため、対象 code を限定して DELETE → INSERT の冪等書き込み
      - API キーは引数または環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）
  - regime_detector:
    - score_regime: ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み
      - マクロニュースはキーワードマッチによりタイトルを抽出（最大記事数制限）
      - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
      - レジーム合成スコアの閾値により 'bull' / 'neutral' / 'bear' を判定
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、失敗時は ROLLBACK を試行し例外を上位へ伝播
      - API キーは引数または環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）
  - OpenAI 呼び出しはテスト時に差し替え可能（内部呼び出し関数に対して unittest.mock.patch を想定）

- 監視 DB (kabusys.monitoring.monitoring_db)
  - init_monitoring_db: SQLite を用いた監視ログ永続化用スキーマを作成（冪等）
    - system_status, trade_logs, positions, risk_logs など複数テーブルとインデックスを生成（5 テーブル + インデックスを作成する設計）
    - ビジネスロジックを持たない読み書きレイヤーとして実装

Changed
- なし（初回リリース）

Fixed
- 初版として以下の堅牢化を実施（バグ修正ではなく意図的な安全策・例外処理）
  - OpenAI レスポンスの JSON パースが壊れている場合に外側の {} を抽出して復元するロジックを追加
  - API エラー/例外に対し再試行／フォールバック（ログ出力）することで処理継続性を確保
  - DB 書き込みにおいてトランザクション失敗時は ROLLBACK を試みる実装を追加
  - ファクター計算やポジション算出でデータ不足時は None や空結果で安全に動作するようにした

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。ログにキー本体を出力しない実装。

Notes / Known limitations / TODO
- sector_exposure の price 欠損時（0.0）によりエクスポージャーが過小見積りされる可能性がある旨の TODO が存在。将来的に前日終値や取得原価等をフォールバック価格として導入予定。
- position_sizing の lot_size は現状全銘柄共通の 100 を想定。将来的に銘柄別単元サイズを受け取る拡張が想定されている（stocks マスタの lot_size 等）。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API を呼ばない設計。実行には DuckDB 接続と適切なテーブル準備が必要。
- news_nlp / regime_detector は外部 LLM に依存するため、API 利用制限やコストに注意。失敗時は部分的にフォールバックするが、完全な代替ロジックは未提供。
- タイムゾーン取り扱い: news ウィンドウは JST を基準に内部で UTC naive datetime を返す設計。運用環境では保存データが UTC であることを前提としている点に注意。
- DuckDB executemany の空リストバインド制約（0.10）を考慮した実装が含まれる（空であれば executemany を呼ばない）。
- 一部モジュール内のコメントに将来的拡張や改善点（TODO）が残る。

環境変数（主なもの）
- 必須（使用機能に応じて）
  - JQUANTS_REFRESH_TOKEN（J-Quants）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（AI モジュールを利用する場合）
- 任意 / デフォルトあり
  - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（データベースパス。デフォルト値あり）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - その他（PID ファイルパス、監視閾値、PAPER_FILL_MODE 等）

利用開始メモ
- プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- AI 機能を利用する場合は OPENAI_API_KEY を設定してください。
- DuckDB / SQLite の対応テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を準備してください。

以上。必要であれば各項目をさらに細分化してコミット単位やファイル別の変更履歴に展開します。