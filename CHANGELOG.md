Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。
このプロジェクトは https://keepachangelog.com/ja/ のガイドラインに概ね従います。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)
- 既知の問題 / 注意点 (Known issues / Notes)

Unreleased
----------

なし。

0.1.0 - 2026-04-09
------------------

Added
- 基本パッケージ初期リリース。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - パッケージの公開インターフェースを __all__ で整理（data, strategy, execution, monitoring 等）。
- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数からの設定値読み込み機能を提供。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - 環境値参照用 Settings クラスを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値、システム環境等）。
  - 入力値のバリデーション: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証と不正値時の例外。
- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定ユーティリティ
    - select_candidates: スコア降順・同点時 signal_rank によるタイブレークで上位 N を選出。
  - 重み計算
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による配分。全スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - リスク調整
    - apply_sector_cap: セクター集中上限チェック（既存保有比率が閾値を超える場合、新規候補を除外）。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返却。未知レジームは 1.0 でフォールバック（警告ログ）。
  - 株数決定・位置サイズ
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。単元株（lot_size）で丸め、max_position_pct による per-stock 上限、利用可能現金に基づく aggregate cap を実装。
    - cost_buffer により手数料/スリッページを保守的に見積り、スケールダウンと端数調整（fractional remainder による lot 単位配分）を行う。
    - lot_size 将来的拡張用にコメントと TODO を追加。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB から計算。必要行数不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range を厳密に NULL 管理して不正評価を防止。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS 欠損や 0 の場合は None）。最新財務レコード選択に ROW_NUMBER を使用。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証（1..252）を実施。
    - calc_ic: Spearman（ランク相関）に基づく IC を計算。有効レコードが 3 未満の場合は None。
    - rank / factor_summary: タイ処理（同順位を平均ランク）を含むランク関数と、count/mean/std/min/max/median を返す統計要約。
  - DuckDB のみを参照し、外部 API には依存しない設計。
  - zscore_normalize を kabusys.data.stats から再公開（__all__ に含める）。
- AI 機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを取得。
    - バッチサイズ、文字数・記事数上限、JSON Mode の利用、レスポンスバリデーション、スコアの ±1.0 クリップ等を実装。
    - リトライ戦略（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。API 失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
    - 書き込みは部分失敗を考慮し、該当コードのみ DELETE → INSERT（トランザクション）で上書き。DuckDB executemany の空リスト制約に対応。
    - calc_news_window: JST ベースのニュースウィンドウを計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - OPENAI_API_KEY の未設定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードフィルタで抽出、LLM 呼び出しは記事がある場合のみ実行。API 失敗時は macro_sentiment=0.0 でフォールバック（警告ログ）。
    - 冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。OPENAI_API_KEY が未設定の場合は ValueError。
    - news_nlp の calc_news_window を再利用（モジュール間で時間ウィンドウ整合）。
- 監視ログ永続化（kabusys.monitoring.monitoring_db）
  - SQLite ベースの MonitoringDB 初期化関数を実装（system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等作成）。
  - ビジネスロジックを持たない単純な読み書き層として提供。

Changed
- 初回リリースのため変更履歴なし。

Fixed
- 初回リリースのため修正履歴なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API を使う機能（news_nlp, regime_detector）は実行時に OPENAI_API_KEY が必要。未設定時は ValueError を送出して明示的に停止する。
- .env 自動読み込みはデフォルトで有効だが、テストや CI で必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Known issues / Notes
- position_sizing.calc_position_sizes:
  - price が欠損（<=0）の場合は当該銘柄をスキップする。TODO にて前日終値等のフォールバックを検討。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map へ拡張する予定。
- apply_sector_cap:
  - sector_map に存在しない銘柄は "unknown" 扱いとなり、セクター上限適用外となる設計。
- research モジュール:
  - 各集計は必要行数不足時に None を返す設計（欠損データに対して安全側）。
- DuckDB の executemany における空リストバインド制約に対して防御実装あり（空の params は送らない）。
- AI モジュールの JSON パースは堅牢化しているが、LLM 出力の想定外フォーマットに起因する失敗はあり得る。失敗時は当該チャンク/呼び出しをスキップして継続するフェイルセーフ戦略を採用。
- 日時取り扱いはルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない実装方針。

今後の予定（短中期）
- 銘柄別 lot_size をサポートするための lot_map 拡張。
- price のフォールバックロジック（前日終値 / 取得原価など）の追加。
- さらなるユニットテスト整備（特に AI 呼び出し部分のモックを含む）。

もしリリースノートや項目の補足説明が必要でしたら、どの部分を詳述するか教えてください。