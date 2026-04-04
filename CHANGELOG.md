Changelog
=========

すべての注記は Keep a Changelog 規約に準拠します。  
このプロジェクトの初期リリースに関する主要な追加・設計方針・品質改善点を、コードベースから推測して日本語でまとめています。

Unreleased
----------

- （現時点の未リリース変更はありません）

0.1.0 - 2026-04-04
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - エクスポートモジュール指定: data, strategy, execution, monitoring を __all__ に公開。

- 環境変数/設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（src/kabusys/config.py）。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理（クォート有無での振る舞い差分）を実装。
    - ファイル読み込み失敗時に警告を出す安全設計。
  - Settings クラスを公開（settings = Settings()）。主要設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev サポート

- AI（OpenAI）統合
  - ニュース NLP スコアリングモジュール（src/kabusys/ai/news_nlp.py）を追加
    - target_date に対するニュースウィンドウを計算する calc_news_window を実装（JSTベース→UTC換算）。
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、gpt-4o-mini（JSON Mode）へバッチ送信して銘柄別センチメントを取得。
    - バッチサイズ、記事・文字数上限、リトライ（指数バックオフ）などの保護ロジックを実装。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB への冪等保存（DELETE → INSERT）および部分失敗時に既存スコアを保護する設計。
    - 空入力やAPI失敗時は安全にスキップし、例外は上位へ投げないフェイルセーフ実装。
    - 公開API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数（int）。

  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）を追加
    - ETF 1321（Nikkei-linked ETF）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価を実装。
    - API 再試行、5xx の取り扱い、失敗時は macro_sentiment=0.0 としてフォールバックする安全設計。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時はROLLBACKを試行して例外を伝播。
    - 公開API: score_regime(conn, target_date, api_key=None) → 1（成功）

- データ基盤（Data）
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）を追加
    - ETLResult dataclass を導入（target_date, fetched/saved counts, quality_issues, errors 等）。to_dict メソッドで監査用辞書化可能。
    - 差分更新、バックフィル、品質チェックフローを想定した設計（J-Quants クライアント呼び出しを想定）。
    - DuckDB 存在確認ユーティリティ等を実装。

  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）を追加
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック。
    - calendar_update_job により J-Quants からカレンダー差分取得→冪等保存（バックフィル、健全性チェックを含む）。

  - ETL/保存に関する互換性配慮:
    - DuckDB の executemany が空リストを受け付けない点に配慮した実装（空チェックを行う）。

- リサーチ／ファクター群（src/kabusys/research）
  - factor_research モジュールを追加（calc_momentum, calc_volatility, calc_value）
    - Momentum: 1M/3M/6M リターン、200日MA乖離（必要行数不足時は None）
    - Volatility: 20日 ATR、ATR比率、平均売買代金、出来高比率
    - Value: PER（EPSが0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB 内の SQL ウィンドウ関数を活用し、prices_daily / raw_financials 参照のみで完結する設計。
  - feature_exploration モジュールを追加（calc_forward_returns, calc_ic, rank, factor_summary）
    - 将来リターン（horizons デフォルト [1,5,21]）を一回のクエリで取得する実装。
    - Spearman IC（ランク相関）計算の実装（ties の平均ランク処理を含む）。
    - 基本統計量（count/mean/std/min/max/median）を算出するユーティリティ。

Changed
- 設計上の方針・注意点を明文化（コード内 docstring に記載）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計を徹底。
  - OpenAI 呼び出し関数はモジュール間で共有するのではなく、それぞれ独自に実装（テスト時の patch を想定）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に影響範囲を限定する。

Fixed / Robustness
- OpenAI API へはリトライ（指数バックオフ）と明確な例外ハンドリングを実装
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx はリトライ対象。その他は基本スキップしログ出力。
  - JSON レスポンスパース失敗時のフォールバック（最外の {} を抽出して復元）やキー・型チェックを実装し、不正応答からの安全復帰を図る。
- 数値検証とクリッピング
  - LLM からのスコアは数値変換可能か、有限値かを確認し、定義範囲（例: ±1.0）でクリップする。
- DuckDB 特有の互換性対応
  - executemany に空リストを渡さない安全チェック（DuckDB 0.10 の制約に対応）を追加。
- ロギング・警告の強化
  - データ不足やAPIエラー、ROLLBACK 失敗などの状況で適切に警告/例外を出力するように実装。

Security
- APIキー取り扱い
  - OpenAI API キーは引数で注入可能、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗させる。

Notes / Implementation details
- 多くの処理（AI スコアリング、レジーム判定、ETL、カレンダー管理、ファクター計算）は DuckDB 接続を引数に取り、外部副作用（発注等）を持たない設計。テスト容易性が高い。
- .env の自動ロードはパッケージファイル位置からプロジェクトルートを探索（.git または pyproject.toml を基準）するため、CWD に依存しない。
- jquants_client（外部モジュール想定）との組合せでカレンダー/ETL を実行する設計を前提としている。

今後の見込み（推測）
- strategy / execution / monitoring モジュールの実装（パッケージトップでエクスポート予定）
- 更なる品質チェック、モニタリング（監視閾値の活用、PID/KILL フラグ連携）の強化
- テスト用のモック・フェイクデータ、CI 対応の充実

---
注: 本 CHANGELOG は与えられたコードベースの内容から推測して作成した初期リリース向けの記述です。実際のコミット履歴やリリースノートに合わせて適宜調整してください。