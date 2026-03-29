# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: この CHANGELOG はリポジトリ内のコードから推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」のコア機能をパッケージ化しました。
主な追加点、設計方針、フェイルセーフなどを以下にまとめます。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - top-level の公開モジュールとして data, strategy, execution, monitoring を想定した __all__ を定義。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - OS 環境変数を保護するため、既存の OS 環境変数は上書きされない実装（.env.local は override=True だが protected を尊重）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パースロジックを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、行末コメント判定など）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等の取得をラップ。
  - env 値の検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェック。
  - デフォルト DB パス（DuckDB / SQLite）を設定。

- AI（NLP）モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを評価。
    - JST 時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事収集（UTC 変換実装）。
    - バッチ処理（最大 20 銘柄／コール）、記事数・文字数のトリム、JSON Mode を利用した厳格な出力期待。
    - 再試行（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフと適切なログ出力。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアのクリップ）。
    - DuckDB への冪等書き込み：取得済み銘柄のみ DELETE → INSERT して既存データの部分失敗を回避。
    - フェイルセーフ設計（API 失敗時は該当チャンクをスキップして残りを処理）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（225 連動型）の200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照してマクロニュースタイトルを抽出し、OpenAI をコールして macro_sentiment を取得。API 失敗時は 0.0 にフォールバック。
    - レジームスコアの合成、閾値判定、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは専用の内部関数を用いており、モジュール間の結合を低減。
    - API リトライ（RateLimit / 接続エラー / タイムアウト / 5xx）を実装。

- データ関連（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを元に営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データがない場合の曜日ベースフォールバック（休日: 土日）。
    - カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得 → 保存）。バックフィル、健全性チェック、保存結果のログ出力あり。
    - 最大探索日数やバックフィル日数等の安全パラメータを設定して無限ループや異常データを防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.ETLResult を再エクスポート）。
    - 差分取得ロジック、最終取得日の取得ユーティリティ、保存・品質チェックの実装方針を明記（J-Quants クライアント / quality チェック連携を想定）。
    - _table_exists / _get_max_date 等の DB ヘルパーを実装。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算する calc_momentum を実装。データ不足時は None を返す。
    - Volatility / Liquidity: 20日 ATR、ATR の割合（atr_pct）、平均売買代金、出来高比率を計算する calc_volatility を実装。true_range の NULL 伝播を考慮。
    - Value: raw_financials から最新財務情報を取得し PER / ROE を計算する calc_value を実装。
    - 全関数とも DuckDB の prices_daily / raw_financials のみを参照し、外部発注や API 呼び出しは行わない設計。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、データ不足時は None）。
    - IC（Spearman の ρ）計算 calc_ic（rank ユーティリティを内部実装）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - rank: 同順位は平均ランクを付与するランク関数を実装。丸め誤差対策あり。
  - research パッケージの __init__.py により主要ユーティリティを再エクスポート。

- モジュール公開
  - ai パッケージで score_news を公開（src/kabusys/ai/__init__.py）。
  - data.etl が ETLResult を再エクスポート。

### Changed
- （初回リリースのため、変更履歴はありません）

### Fixed
- （初回リリースのため、修正履歴はありません）

### Security
- 環境変数の自動読み込み時に OS 環境変数を保護する実装により、意図しない上書きを防止。

### Notes / Design decisions
- いずれのモジュールも datetime.today() / date.today() を直接使用しない設計（ルックアヘッドバイアス防止）。すべての日時は呼び出し側から明示的に渡す（target_date 等）。
- OpenAI（gpt-4o-mini）呼び出しは JSON Mode を期待するが、厳密な JSON が返らないケースに備えたパース回復処理を実装。
- DuckDB 0.10 等の制約（executemany に空リスト渡せない等）に配慮した実装。
- API キー（OPENAI_API_KEY）は関数引数で注入可能。未設定時は明示的に ValueError を投げる。
- 冪等性を重視した DB 操作（DELETE → INSERT など）で再実行可能性を確保。
- ロギングを多用し動作状況・異常時の情報を残す方針。

### Dependencies / Requirements (明示)
- duckdb
- openai（OpenAI SDK を利用）
- J-Quants クライアントモジュール (kabusys.data.jquants_client を想定)
- 実行環境での環境変数設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を必要とする機能あり。

---

今後のリリースにて、strategy / execution / monitoring モジュールの具現化、テストケース・CI、型チェックの強化、ドキュメント（ユーザーガイド・設計ドキュメントの切り出し）などを記載していく予定です。