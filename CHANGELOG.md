CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" のフォーマットに従って記載しています。  
このファイルでは、機能追加、改善、バグ修正などの変更点をバージョン単位でまとめています。

目次
- [Unreleased](#unreleased)
- [0.1.0] - 2026-04-03

Unreleased
----------
（なし）

0.1.0 - 2026-04-03
------------------

初期公開リリース。本リポジトリは日本株のデータ取得・前処理・研究・AIベースのニュース評価・市場レジーム判定・ETL ジョブなどを扱う自動売買／リサーチ基盤として以下の主要機能を実装しています。

Added
- パッケージ基盤
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - メインサブパッケージ公開: data, research, ai, execution, monitoring, 等のモジュール構成を想定する __all__ を定義。

- 環境・設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト時に便利）。
  - .env の行パーサを独自実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱い等に対応。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パスなど多数のプロパティ）。未設定時の必須項目チェック（_require）や値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - パス系設定は Path オブジェクトで返却、デフォルト値を用意（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など）。
  - 監視用しきい値（CPU/メモリ/ディスク%）や kill flag の挙動など、運用設定をプロパティで公開。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini, JSON mode) によるセンチメント評価を行い ai_scores テーブルに書き込み。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30、DB 比較は UTC naive datetime に変換）。
    - バッチ処理: 1 回の API コールで最大 20 銘柄（_BATCH_SIZE）、1銘柄あたり記事数・文字数のトリム制御（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API リトライ戦略（429 / ネットワーク / タイムアウト / 5xx を対象に指数バックオフ）。
    - レスポンスの厳密バリデーションと冗長テキストからの JSON 抽出ロジック。
    - スコアを ±1.0 にクリップ。
    - DuckDB 0.10 の executemany 空リスト制約を考慮した安全な書き込みロジック（DELETE → INSERT、それぞれ空チェック実施）。
    - テスト用フック: _call_openai_api を patch しやすい設計。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（Nikkei225 連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルに書き込み。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを決定し、タイトルを抽出して LLM に投げる。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない設計）。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - レジーム判定結果はクリップ・閾値判定（bull / neutral / bear）して market_regime に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を伝播。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを使った営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は休業）を一貫して利用。
    - 最大探索日数制限を設け、無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）・保存（jquants_client 経由）を実装。健全性チェック（未来に過剰に飛んでいる last_date の検出）を有する。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを定義し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返却・変換可能にした。
    - 差分更新・バックフィル・品質チェック（quality モジュール利用）を想定した設計。主要定数（_MIN_DATA_DATE, backfill など）を定義。
    - jquants_client を経由した idempotent 保存の想定（save_* 関数で ON CONFLICT / upsert を行う方針）。

- Research モジュール (kabusys.research)
  - factor_research.py
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）、ボラティリティ（atr_20, atr_pct）、流動性（avg_turnover, volume_ratio）、バリュー（per, roe）などの定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB による window 関数等を活用し、営業日ベースの窓を考慮。
    - データ不足時は None を返す安全設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns、可変ホライズン、入力検証、まとめて1クエリで取得する最適化）。
    - IC（スピアマンのランク相関）計算（calc_ic）。NaN/None の除外、3 銘柄未満では None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクを採用、浮動小数の丸め（round 12 桁）による ties 対応。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median の算出。
  - research パッケージ __all__ に主要関数を再公開。

Changed / Design decisions（ドキュメント化）
- ルックアヘッドバイアス防止
  - 各 AI / 研究処理は内部で datetime.today()/date.today() を直接参照しない設計。外部から target_date を与えることで過去限定のデータのみを参照する。
- フェイルセーフ指針
  - 外部 API（OpenAI / J-Quants）失敗時に全停止させず、局所的にデフォルト値（例: macro_sentiment=0.0）を使って処理継続する方針を採用。
- テスト容易性
  - OpenAI 呼び出し関数に patch 可能な内部関数（_call_openai_api）を用意しており、ユニットテストでモックに差し替え可能。
- DuckDB 互換性への配慮
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮したガード実装。

Fixed
- 初期リリースのため、既知のバグ修正履歴はなし。

Security
- API キーは明示的に引数で注入可能（api_key 引数）で、未設定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出して誤使用を防止。

Notes / Implementation details
- OpenAI とのやり取りは gpt-4o-mini を用い、JSON Mode（response_format={"type": "json_object"}）を利用する想定で実装。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計（結合度低減）。
- レスポンスのパース失敗や想定外の構造はログ出力してスキップまたはフォールバックする（例: JSONDecodeError → 0.0 / 空辞書）。
- レコード書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT 想定）ことで再実行や部分失敗に強くしている。

今後の予定（例）
- ai モジュールの追加テストとモック基盤整備
- jquants_client の具体実装と ETL パイプラインの公開 API 実装（差分取得ロジックの完成）
- 監視（monitoring）および実取引 execution モジュールの安全実装とテスト
- ドキュメント（StrategyModel.md / DataPlatform.md）に合わせた詳細ドキュメント整備

---

この CHANGELOG はコードの内容から想定される実装・設計方針・挙動を基に作成しています。実際のリリースノートに採用する際は、差分や変更点を開発履歴（コミットログ等）と照合して調整してください。