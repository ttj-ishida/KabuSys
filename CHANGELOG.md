Changelog
=========

すべての重要な変更をここに記録します。これは "Keep a Changelog" の形式に従っています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Security）ごとに分類しています。
- バージョンはパッケージ内の __version__（0.1.0）に合わせています。

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョンと主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 環境設定・ロード機能
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - .env のパースは export 形式・クォートやエスケープ・インラインコメント等に対応する堅牢な実装。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 環境変数取得ユーティリティ _require と Settings クラスを提供。J-Quants / kabuステーション / LINE / DB / 監視 / システム設定項目をプロパティで公開。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値セットによるバリデーション）。
    - Path 型でのデフォルトパス（duckdb, sqlite, pid, kill flag 等）を提供。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元にニュースを銘柄毎に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して処理（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数と文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク・5xx に対する指数バックオフによる再試行ロジック。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。部分失敗時に既存スコアを保護するための部分置換（DELETE → INSERT）実装。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI 呼び出し、スコア合成、マクロ失敗時は 0.0 フェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の取り扱い。OpenAI 呼び出しに対する再試行設定とログ出力。

- データ/ETL 機能
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult dataclass（target_date, fetched/saved counts, quality_issues, errors 等）を公開（etl.py で再エクスポート）。
    - 差分更新、バックフィル（デフォルト数日）、品質チェック統合（quality モジュール参照）を想定した設計。
    - DuckDB を前提としたテーブル存在確認、最大日付取得ユーティリティ等を実装。executemany の空リスト扱い等 DuckDB 特性への配慮を含む。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）とマーケットカレンダーの夜間差分更新ジョブ calendar_update_job 実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - calendar_update_job は J-Quants クライアントを用いた差分取得・バックフィル・健全性チェック（未来日の不正検出）・保存のフローを実装。
    - DB 登録有無に応じた「DB 値優先、未登録は曜日ベースでフォールバック」という一貫した挙動。

- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - Volatility: 20 日 ATR（平均 true range）、ATR 比率、20 日平均売買代金／出来高変化率を計算。
    - Value: raw_financials から EPS/ROE を参照し PER と ROE を算出（EPS が 0/欠損の場合は None）。
    - DuckDB 上の SQL ウィンドウ関数を利用し、高速に計算する設計。戻り値は (date, code) を含む dict のリスト。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、ランク変換(rank)、統計サマリー(factor_summary) を実装。
    - 外部依存を避け、標準ライブラリのみで数値処理を実装。horizons の入力検証や ties の平均ランク処理など考慮。

- ユーティリティ・エクスポート
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, src/kabusys/data/__init__.py 等で主要関数を公開。
  - research パッケージは zscore_normalize（data.stats 由来）を再エクスポート。

Notes / Implementation details
- OpenAI 関連
  - 使用モデルは gpt-4o-mini。JSON Mode を期待するプロンプト設計（厳密な JSON 出力を要求）。
  - API 呼び出しの再試行（429, ネットワーク, タイムアウト, 5xx）とバックオフ実装。非 5xx APIError は即時失敗として扱う箇所あり。
  - レスポンスパース失敗や API 完全失敗時は例外を投げずにフェイルセーフ（0.0 やスキップ）で継続する設計。運用時の可用性重視。

- DuckDB / DB 周辺
  - 多数の処理は DuckDB 接続を受け取り SQL を実行する設計（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials 等）。
  - executemany に関する DuckDB の制約（空リスト不可）に対する防御ロジックを実装。
  - すべての日付は datetime.date / naive datetime で扱い、タイムゾーン混入を避ける方針。

- テストフック
  - OpenAI 呼び出しを隠蔽した内部関数（_call_openai_api）を各モジュールで実装しており、テスト時に patch して挙動を模擬可能。

- 設計上の注意点 / 未実装
  - calc_value: PBR・配当利回りは現バージョンで未実装（注記あり）。
  - 本リリースは「データ取得・解析・スコアリング」のライブラリ層が中心であり、実際の発注（kabu ステーションへの発注）や Strategy の自動実行ロジックは別モジュール（strategy, execution）として想定されているが、本差分では主にデータ・研究・NLP 周りを実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （初版のため該当なし）

タグ
- 本 CHANGELOG はパッケージ内の docstrings とコード構造から推測して作成されています。実際に公開する CHANGELOG として使用する場合は、リリース時の実際のコミット履歴・影響範囲に合わせて調整してください。