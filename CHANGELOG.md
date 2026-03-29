KEEP A CHANGELOG
================

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」規約に準拠します。
履歴は semver（意味的バージョニング）に従います。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース。
- パッケージ概要
  - kabusys: 日本株自動売買／リサーチ用ライブラリの初期実装を追加。
  - __version__ を "0.1.0" に設定。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサーは export 形式やクォート、行内コメント、エスケープを取り扱う。
  - 必須環境変数を取得する _require と Settings クラスを提供。
  - Settings で想定される環境変数（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を元にニュースを銘柄別に集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数制限・文字数トリム）、JSON Mode レスポンスの妥当性チェック、429/ネットワーク/5xx の指数バックオフリトライを備える。
    - calc_news_window により JST に基づくニュース収集ウィンドウ（前日15:00〜当日08:30 JST）を計算。
    - API キー未設定時は ValueError を送出。
    - 外部に依存しない設計（DuckDB 接続を受ける、datetime.today を使わない等）でルックアヘッドバイアスを防止。
  - regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込みを行う実装。
    - OpenAI 呼び出しは専用実装で取り扱い、API エラー時のフォールバック（macro_sentiment = 0.0）を備える。
    - ルックアヘッド防止のため DB クエリは target_date 未満・同日排他等の条件で実装。
    - API 呼び出しはリトライ・バックオフを実装（最大試行回数・待機時間制御）。

- データモジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブル）: 営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間バッチ更新 calendar_update_job を実装。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末を休業日扱い）。
    - calendar_update_job は J-Quants クライアント経由で差分取得し冪等保存、バックフィル・健全性チェックを実装。
  - pipeline / etl
    - ETL パイプラインの骨組みを実装。ETLResult データクラスを公開（kabusys.data.ETLResult を etl 経由で再エクスポート）。
    - 差分取得ロジック、バックフィルの考慮、品質チェックの統合設計（quality モジュールに依存）を反映。
    - ETLResult は処理結果（取得数・保存数・品質問題・エラー等）を集約し、dict 変換メソッドを提供。

- リサーチモジュール（kabusys.research）
  - factor_research
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比率など。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時の None ハンドリングを行う。
  - feature_exploration
    - calc_forward_returns: 指定 horizon（営業日）先までの将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算を実装（欠測・データ不足時の扱いあり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを返す実装（丸め対策あり）。
    - 実装は標準ライブラリのみ依存（pandas 等非依存）で設計。

- 共通実装・設計方針
  - DuckDB を主要なローカル分析 DB として想定。
  - ルックアヘッドバイアス防止の徹底（datetime.today()/date.today() を直接参照しない設計）。
  - OpenAI API 呼び出しに対して堅牢なリトライ・バックオフ・フォールバックを実装。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT 等）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で安全性を確保。
  - テスト容易性のため、OpenAI 呼び出し箇所は単体テストで差し替え可能に設計（内部 _call_openai_api の patch を想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは環境変数/ .env 経由で扱う想定。コード内にハードコードされた機密情報は含まれない。

Notes / Known limitations
- DuckDB のバージョン差異により executemany に関する挙動（空リスト不可等）を回避するための防御コードが含まれる。
- OpenAI API の JSON Mode に依存する箇所があるため、将来的な SDK/モデル変更での挙動確認が必要。
- 一部の集約処理は大量データを扱うとメモリ/CPU 負荷が発生する可能性がある（初期実装のため最適化の余地あり）。
- Python の型ヒントに union 表記 (Path | None 等) を使用しているため Python 3.10+ を想定。

Authors
- 初期実装: 開発チーム（コードベースより推測して記載）

License
- プロジェクトのライセンスはリポジトリ内の LICENSE に従うこと。

--- 

（以上）