Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
------------

（現在未リリースの変更はありません。）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に追加。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に検出（CWD 非依存）。
  - .env パーサを強化:
    - 空行・コメント行の無視、export プレフィックス対応、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォート無し行でのインラインコメント判定（直前がスペース/タブの場合のみ）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境値アクセス用 Settings クラスを実装（必須キーは _require で検証）。
  - 各種設定プロパティを提供:
    - J-Quants、kabuステーション API、Slack、DB パス（duckdb/sqlite）、実行環境（development/paper_trading/live）、ログレベル、is_live/is_paper/is_dev 判定。
  - 環境変数値の検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management:
    - JPX カレンダー管理、market_calendar テーブルを用いた営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、NULL 値の警告など堅牢化。
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存（バックフィル、健全性チェック）。
  - ETL インターフェース（etl.py）:
    - pipeline.ETLResult を公開（再エクスポート）。
  - pipeline モジュール:
    - ETLResult dataclass を実装（取得数／保存数／品質問題／エラー情報などを保持）。
    - 差分更新・バックフィル方針、品質チェックの結果保持、DuckDB テーブル存在確認などのユーティリティを実装。
    - jquants_client および quality モジュールと連携する設計（API 呼び出しを注入可能にしてテスト容易性確保）。

- AI モジュール（src/kabusys/ai/*）
  - news_nlp:
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算 calc_news_window（JST ベースの前日15:00〜当日08:30）を実装。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1銘柄あたり記事数上限・文字数トリム対策を実装。
    - API 呼び出しのリトライ／エクスポネンシャルバックオフ（429・接続断・タイムアウト・5xx 対象）、API エラーの扱い（非5xx は即スキップ）を実装。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results 配列形式、コード照合、数値検証、スコアの ±1 クリップ）。
    - ai_scores テーブルへは部分失敗に強い「DELETE（対象コード）→ INSERT（対象コード）」の冪等更新を実装。
    - score_news 関数をパブリック API として公開（書き込み銘柄数を返す）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp を使ったマクロセンチメント（重み 30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）とマクロ記事抽出ロジックを実装。
    - OpenAI API 呼び出し（gpt-4o-mini）を用いたマクロセンチメント評価、リトライ／フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - スコア合成と閾値判定（BULL/BEAR）、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - score_regime 関数をパブリック API として公開（成功時 1 を返す）。

- リサーチ（src/kabusys/research/*）
  - factor_research:
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性指標（20日平均売買代金・出来高比）などのファクター計算関数を実装。
    - DuckDB を直接利用する SQL ベースの実装。データ不足時の None 取り扱いを明確化。
    - 関数: calc_momentum, calc_volatility, calc_value（raw_financials と結合して PER/ROE 計算）。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（複数ホライズンを一度に取得する SQL 実装）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関の実装、最小有効レコード数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - 全体的に pandas 等に依存せず、標準ライブラリ + DuckDB で完結する実装。

- API / エクスポート整理
  - kabusys.ai.__init__ で score_news をエクスポート。
  - kabusys.research.__init__ で主要なリサーチ関数群を再エクスポート。
  - kabusys.data.etl で ETLResult を再エクスポート。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- （このリリースにおける既知のセキュリティ修正はありません）

Notes / 実装上の注意
- すべての処理でルックアヘッドバイアスを避ける方針を採用（datetime.today()/date.today() を直接参照しない実装）。
- OpenAI 呼び出しに関するテスト向けの差し替えポイントを設けている（各モジュール内の _call_openai_api を unittest.mock.patch でモック可能）。
- DuckDB の executemany に空リストを渡せないバージョン互換性を考慮した保護（空リストチェック）を実装。
- 外部 API（J-Quants / OpenAI / kabuステーション）のキーやエンドポイントは環境変数で提供するよう設計。必須キー未設定時には明示的なエラーを発生させる。

Acknowledgements
- このリリースはデータプラットフォーム、AI ベースのニュース解析、研究用ファクター群、および ETL/カレンダー管理を統合する初期実装を提供します。今後はドキュメント・テスト・パフォーマンス改善・運用監視の強化を予定しています。