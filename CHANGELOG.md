# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に従います。

全項目はソースコードから推測した内容に基づき記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - top-level:
    - src/kabusys/__init__.py によるパッケージ公開（data, strategy, execution, monitoring）とバージョン設定（__version__ = "0.1.0"）。

- 環境設定・自動.envロード:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加。
    - 読み込み優先順: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env パース機能: export 接頭辞、シングル/ダブルクォート内のエスケープ、行内コメントの扱い等をサポート。
    - 必須設定の取得用ヘルパー _require と Settings クラスを追加。よく使う環境変数をプロパティで公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 必要時、KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値を限定）。

- AI モジュール（OpenAI を用いたニュースセンチメント等）:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）に投げることで銘柄毎の ai_score を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたりの最大記事数・文字数制限、レスポンスバリデーション（JSON抽出・results 配列・コード一致・数値検証）、スコアの ±1.0 クリップを実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実施。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB への冪等書き込み（DELETE → INSERT）に備え、部分失敗時に既存スコアを保護する実装。
    - テスト用フック: _call_openai_api を patch 可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。OpenAI API キー未設定時は ValueError。

  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定するアルゴリズムを実装。
    - prices_daily / raw_news を参照して ma200_ratio を算出、マクロキーワードで記事をフィルタして LLM に投げ、合成スコアを計算。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を備える。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。OpenAI API キー未設定時は ValueError。

- データ（Data Platform）機能:
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - market_calendar が未登録の場合は曜日ベース（土日休み）でフォールバックする一貫性のある設計。
    - calendar_update_job(conn, lookahead_days=...) により J-Quants から差分取得して market_calendar を冪等更新（バックフィルや健全性チェック含む）。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの骨組みを実装。差分取得、保存、品質チェック統合を意識した設計。
    - ETLResult dataclass（target_date, fetched/saved counts, quality_issues, errors）を実装し、状態の集約と to_dict() 出力を提供。
    - 内部ユーティリティで DuckDB 上の最大日付算出やテーブル存在チェックを実装。

  - src/kabusys/data/__init__.py
    - pipeline の ETLResult を再エクスポートする薄いラッパーを提供。

  - J-Quants クライアント呼び出し箇所（jquants_client 経由）を想定した設計。

- リサーチ機能（ファクター・特徴量解析）:
  - src/kabusys/research/factor_research.py
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（per, roe）計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いた実装。結果は (date, code) をキーとする dict のリストで返す。
    - データ不足時の None 処理やログ出力などを含む堅牢な実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC（Information Coefficient）を算出する calc_ic、rank、および統計サマリー factor_summary を実装。
    - pandas 等の外部ライブラリに依存しない純 Python 実装。
    - calc_ic はスピアマンのランク相関（ランク化は平均ランク処理）を実装。

  - src/kabusys/research/__init__.py
    - 主要関数を __all__ で公開（zscore_normalize は kabusys.data.stats からの再利用を想定）。

### Design / Implementation notes
- ルックアヘッドバイアス対策:
  - AI モジュールやリサーチ・ETL の対象日判定において、datetime.today() / date.today() を直接使用しない実装方針を採用。すべて target_date ベースでの計算を行うため再現性が高い。
- フェイルセーフ:
  - LLM 呼び出し失敗やエラー時は、例外を投げずにスコアを 0 や空扱いにして処理を継続する設計（運用上の安全性を優先）。
- 冪等性:
  - DB への書き込みは原則冪等（DELETE → INSERT、ON CONFLICT を想定）で、部分失敗時に既存データを過度に消さない工夫あり。
- DuckDB 互換性のための実装上の注意:
  - executemany に空リストを渡さないチェック、LIST 型バインド回避のための個別 DELETE 実行など、DuckDB バージョン差分に配慮した実装。
- テスト性:
  - OpenAI API 呼び出し関数（_call_openai_api）等は unittest.mock.patch で差し替え可能に設計。

### Requirements / Environment
- 必須環境変数（機能利用時）:
  - OpenAI を使う機能: OPENAI_API_KEY（score_news / score_regime は指定がないと ValueError を投げる）
  - J-Quants 関連: JQUANTS_REFRESH_TOKEN（ETL 等）
  - kabu ステーション API: KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - Slack 通知: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- オプション / デフォルト:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、KABUSYS_ENV（development/paper_trading/live、デフォルト development）、LOG_LEVEL（デフォルト INFO）
- データベース前提テーブル（主な読み書き先）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などが前提（ETL での投入が必要）。

### Security / Privacy
- API キーは環境変数で管理することを想定。.env ファイルの扱いに注意（自動ロード機能あり）。

### Known limitations
- 外部 API クライアント（jquants_client や 実際の kabu API 呼び出し実装）はこのコードに含まれていないため、実行にはそれらの実装/設定が必要。
- gpt-4o-mini などのモデル利用は利用料金が発生するため運用時のコスト管理が必要。

---

注: 本 CHANGELOG は与えられたソースコードの内容・コメントから推測して作成しています。実際のリリースノート作成時には、実際のコミット履歴・PR・ドキュメントと照合して調整してください。