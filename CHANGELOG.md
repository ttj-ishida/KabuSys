Keep a Changelog に準拠した変更履歴

すべての注目に値する変更はこのファイルに記録します。フォーマットについては https://keepachangelog.com/ja/ を参照しています。

Unreleased
- なし

[0.1.0] - 2026-04-09
Added
- パッケージ初期リリース。
- 基本メタ情報:
  - パッケージバージョンを __version__ = "0.1.0" として追加。
  - top-level export: data, strategy, execution, monitoring を __all__ に定義。
- 環境設定:
  - 環境変数/ .env 読み込みモジュールを追加（kabusys.config）。
  - .env 自動ロード機能をプロジェクトルート（.git または pyproject.toml）から行う実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサは以下をサポート:
    - コメント・空行の無視、`export KEY=val` 形式の対応、シングル/ダブルクォートおよびバックスラッシュエスケープの処理、インラインコメントの扱い（クォートあり/なしの差分処理）。
  - 環境値取得ラッパー Settings クラスを追加。主要設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須取得（未設定時に ValueError を送出）。
    - KABU_API_BASE_URL, LINE_*、データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）などのデフォルト値。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。
    - 監視用パス（PID_FILE_PATH, KILL_FLAG_PATH）や閾値（CPU/MEM/DISK）を環境で設定可能。
- ポートフォリオ構築（kabusys.portfolio）:
  - 銘柄選定:
    - select_candidates: BUY シグナルをスコア降順・signal_rank タイブレークで上位 N を選出。
  - 配分重み:
    - calc_equal_weights: 等金額配分の重みを返す。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0.0 の場合は等金額配分にフォールバックし WARNING を出力。
  - リスク調整:
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックし警告ログを出力。
  - 株数決定:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出を実装。
    - risk_based: 許容リスク率・損切り率から目標株数計算。
    - equal/score: 重みから配分を算出。lot_size（デフォルト 100）で丸め、単銘柄上限/max_utilization/aggregate cap を考慮。
    - aggregate cap の超過時はスケールダウンし、余りキャッシュを fractional 残差の大きい順に lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もれるように対応。
- リサーチ（kabusys.research）:
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。ウィンドウ不足時は None を返す挙動。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を行う。
    - calc_value: raw_financials から直近財務データを取得し PER（EPS が 0/欠損の場合は None）・ROE を計算。
    - いずれも DuckDB を受け取り SQL で処理。prices_daily / raw_financials のみ参照、外部 API 呼び出しは行わない設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）先の将来リターンを計算。ホライズンは検証済み（1〜252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（浮動小数丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats）を再エクスポート。
  - すべて純粋関数かつメモリ内計算（DB は読み取りのみ）という設計を明確化。
- AI 関連（kabusys.ai）:
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをスコア化して ai_scores に書き込む機能を実装（score_news）。
    - ニュースウィンドウ計算（calc_news_window）を実装（前日 15:00 JST 〜 当日 08:30 JST 相当、内部は UTC naive）。
    - 記事集約は銘柄ごとに最新 N 件・文字数上限でトリム（MAX_ARTICLES_PER_STOCK, MAX_CHARS_PER_STOCK）。
    - API 呼び出しは最大 BATCH_SIZE（20）銘柄をまとめて送信、JSON Mode を用いて厳密な JSON を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（リトライ回数制限あり）。その他の例外はリトライせずスキップ。
    - レスポンスの厳密なバリデーションを実装。スコアは ±1.0 にクリップ。未知コードは無視。
    - 書き込みは部分失敗に耐えるよう、対象コードのみ DELETE → INSERT の冪等書き込みを行う（DuckDB executemany の制約を考慮）。
    - API キー未設定時は ValueError を発生させる（引数優先、環境変数 OPENAI_API_KEY 参照）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定（score_regime）。
    - ma200_ratio 算出は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）にフォールバックして WARNING を出力。
    - マクロニュースはキーワードフィルタでタイトルを抽出し LLM で macro_sentiment を評価。記事が無い場合や API 失敗時は 0.0 にフォールバック。
    - 合成スコアを閾値で分類し market_regime テーブルへ冪等書き込みを行う。
    - news_nlp の calc_news_window を再利用して時間ウィンドウ整合性を担保。
  - AI モジュールの OpenAI 呼出しはテスト時に差し替えられる設計（内部呼び出しを独立実装）。
- 監視ログ永続化（kabusys.monitoring.monitoring_db）:
  - SQLite を用いて監視関連のテーブルを作成する初期化関数 init_monitoring_db を追加。
  - system_status, trade_logs, positions, risk_logs などのテーブルとインデックスを冪等に作成（複数テーブルを作成するスクリプトを含む）。
- ロギングとエラーハンドリング:
  - 多くの処理で詳しいデバッグ/警告ログを追加。データ不足や API 失敗時はフェイルセーフ（例外を投げずにフォールバック）する箇所を多数用意。
  - DuckDB / SQLite への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。

Changed
- 初版リリースのため変更履歴はありません。

Fixed
- 初版リリースのため修正履歴はありません。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーなどのシークレットは引数または環境変数からのみ読み込み、未設定時は明示的にエラーとなる箇所を用意（不用意なデフォルト出力を避ける）。

Notes / Known limitations / TODO
- portfolio.position_sizing:
  - lot_size は現状全銘柄共通の単純設計。将来的に銘柄別 lot_map を受け取る拡張予定（TODO コメントあり）。
  - 価格（open_prices）に 0.0 が含まれるとエクスポージャー計算で過少見積りになる懸念が記載されている（price フォールバックの検討が必要）。
- research モジュールは DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存。データ準備が必要。
- AI 関連:
  - LLM のレスポンスは稀に JSON 以外のノイズを含むためパーサで復元処理を行っているが、完全ではない可能性あり。
  - OpenAI の SDK 仕様変更に備え、APIError の status_code の参照は getattr を使って安全に行っているが、将来の互換性チェックを推奨。
- monitoring_db のファイルはテーブル定義を含むが、将来的なスキーマ変更・マイグレーション戦略は未実装。

---------- 
脚注:
- 本 CHANGELOG は提供されたコードベースを元に推測して作成しています（実装コメントや TODO も反映）。実際のリリースノートとして使用する際は、実稼働時の差分やバグ修正情報を追記してください。