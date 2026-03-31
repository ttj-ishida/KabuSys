# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠します。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加 (src/kabusys/__init__.py, __version__ = "0.1.0")。

- 環境変数・設定管理
  - settings API を提供する Settings クラスを実装 (src/kabusys/config.py)。
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の優先度と override ロジック（OS 環境変数を protected として保護）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理など。
  - 必須環境変数取得ヘルパー _require、設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL の検証
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。

- AI モジュール
  - ニュース NLP（センチメントスコアリング）機能を追加 (src/kabusys/ai/news_nlp.py)。
    - raw_news / news_symbols を集約して銘柄ごとにテキストをまとめ、OpenAI（gpt-4o-mini）の JSON モードで一括評価。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数のトリム、429/ネットワーク/タイムアウト/5xx の指数バックオフリトライ、レスポンスバリデーション、±1.0でクリップ。
    - calc_news_window(target_date) による対象ウィンドウ計算（JST 基準: 前日15:00 ～ 当日08:30）。
    - テストのため _call_openai_api を patch 可能に設計。
    - スコアを ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT）。
  - 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しは専用実装、API エラー時はマクロセンチメントを 0.0 としてフェイルセーフに継続。
    - DuckDB の prices_daily/raw_news/market_regime を利用し、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。

- データプラットフォーム（Data）モジュール
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの参照・更新ロジックを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 未取得時は曜日ベースでフォールバック、最大探索日数の制限や健全性チェックを導入。
    - calendar_update_job による J-Quants API からの差分取得・保存・バックフィル処理を実装（API 呼び出し用の jquants_client を利用）。
  - ETL パイプライン / ユーティリティ
    - ETLResult データクラスを公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）などの設計指針を実装。
    - DuckDB の最大日付取得やテーブル存在チェック等のヘルパーを実装。

- リサーチ（Research）モジュール
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを calc_volatility で実装。
    - Value: PER・ROE を raw_financials と prices_daily から組み合わせて calc_value を実装。
    - DuckDB 内で完結する設計、データ不足時の None ハンドリング。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（可変ホライズン対応、入力検証付き）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、ランク化処理付き）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。

- パッケージのエクスポート調整
  - research パッケージの __all__ とトップレベル再エクスポートを整備。
  - ai パッケージの公開 API を整備（score_news, score_regime を含む）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 注意点 / 既知の設計方針
- ルックアヘッドバイアス対策として、いずれのモジュールも datetime.today() / date.today() を内部ロジックで参照しない設計を採用（target_date 引数を必須にして外部から与える）。
- OpenAI 呼出し部分はリトライやタイムアウト処理を実装し、API 例外発生時はスコアのフォールバックやスキップを行うことで堅牢性を高めています。
- DuckDB に対する executemany の空パラメータ扱い（バージョン互換性）を考慮して空チェックを行っています（特に ai_scores 書き込み処理）。
- テスト容易性のため、OpenAI API 呼び出し用の内部関数（_call_openai_api）を patch しやすくしています。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

### セキュリティ (Security)
- API キー等の機密情報は環境変数から取得する設計です。必須環境変数が未設定の場合は ValueError を送出して明示的に失敗します。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を採用。

---

将来的なリリースでは、発注（execution）やモニタリング（monitoring）等の運用コンポーネント、より詳細な品質チェック・データ可視化、テストカバレッジの強化などを予定しています。