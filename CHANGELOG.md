CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。
[https://keepachangelog.com/ja/1.0.0/]

なお、本ファイルはコードベースから推測して作成した初期リリースの概要を日本語でまとめたものです。

[Unreleased]
------------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

Added
- 全体
  - 新規パッケージ "kabusys" を追加。主要サブパッケージは data, research, ai, monitoring, execution, strategy（__all__ により公開）。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定。
    - 読み込み順は OS 環境変数 > .env.local (上書き) > .env（未設定時にセット）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env パーサー実装:
    - export KEY=val 形式対応、クォート（' "）とバックスラッシュエスケープ処理、インラインコメントの扱い、無効行対応。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能に：
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 動作環境 / ログレベルなどのプロパティ。
    - 必須値取得時の _require() により未設定時は ValueError を送出。
    - 環境変数名やデフォルト値を明記（例: KABU_API_BASE_URL, DUCKDB_PATH, PID_FILE_PATH 等）。
    - KABUSYS_ENV の検証（development, paper_trading, live）およびログレベル検証機能を追加。

- AI（自然言語処理）(kabusys.ai)
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを生成。
    - OpenAI（gpt-4o-mini）の JSON Mode を使い銘柄毎に -1.0〜1.0 のスコアを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事・文字数トリム、重試行（429 / ネットワーク / タイムアウト / 5xx のエクスポネンシャルバックオフ）。
    - レスポンス検証ロジック（JSON 抽出、results リスト・型検査、未知コードの無視、数値チェック、スコアクリップ）。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）、DuckDB executemany の空リスト回避対応。
    - calc_news_window(): JST ベースのニュースウィンドウ計算（前日15:00～当日08:30 JST を UTC 比較用に変換）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - regime_detector モジュール（score_regime）:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）、マクロニュース抽出、OpenAI 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK ハンドリング。
    - OpenAI API 呼び出しは独立実装としモジュールの結合を避ける設計（テスト差替え可能）。

- Data（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar テーブル）と、営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先だが、データがない場合は曜日ベース（土日休み）でフォールバックする挙動。
    - 探索上限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - calendar_update_job(): J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を使って差分取得・バックフィル・健全性チェック付きで DB を更新する nightly job 実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート）。
    - ETLResult は取得数・保存数・品質チェック結果・エラー一覧を保持し、has_errors/has_quality_errors/properties と to_dict() を提供。
    - ETL パイプライン設計（差分更新、バックフィル、保存は jquants_client の idempotent 関数を使用、品質チェックは収集して呼び出し元に委ねる）に準拠した実装の下地を用意。
    - DuckDB 存在確認や最大日付取得のユーティリティを実装（ETL 処理で使用）。

- Research（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR（平均 true range）、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の EPS/ROE を取得し PER/ROE を計算（EPS 0/欠損時は None）。
    - 各関数は DuckDB の SQL とウィンドウ関数を活用して効率的に計算。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンバリデーションを実施（1〜252）。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。データ不足や分散ゼロ時の None 戻し。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。

- Research / Data 共通設計方針（明記）
  - ルックアヘッドバイアス回避のため、関数内で datetime.today() / date.today() を参照しない設計。
  - DuckDB をデータ層に採用し、executemany の空リスト回避等の互換性考慮を実装。
  - 外部 API 呼び出しは最小化（研究モジュールは API 非依存）やフェイルセーフ（API 失敗時はスキップ/0フォールバック）を採用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （現時点で該当なし）

Removed
- （現時点で該当なし）

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を想定し、未設定時は明示的に ValueError を発生させる仕様を導入（誤ったキー運用を早期に検出）。

Notes / 実装上の注意点
- OpenAI 呼び出しは JSON Mode を利用する想定。レスポンスの堅牢なパースやリトライロジックを備えているが、実環境でのモデル挙動に依存するため追加の監視やログが推奨される。
- DuckDB に対する SQL や executemany の振る舞いはバージョン差異に影響を受けるため、運用時は使用している DuckDB バージョンでの動作確認を推奨。
- news_nlp と regime_detector はいずれも _call_openai_api の差替えを想定しており、テストでのモック化が容易。
- .env パーサーはシェルライクな形式にかなり対応しているが、極端に複雑なケースは想定外となる可能性がある。

今後の予定（示唆）
- ai スコアや market_regime を利用した実トレード戦略（strategy / execution）と監視（monitoring）の実装・統合。
- ETL の品質チェックルール拡充と自動アラート機構。
- テストカバレッジ強化と CI 統合。

もしこの CHANGELOG の内容について補足すべき点や、実際のコミットメッセージに合わせた調整が必要であれば、対象のコミットや差分を教えてください。