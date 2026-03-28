# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトの初回リリース (0.1.0) に含まれる主な機能・設計方針・注意点を要約しています。

ドキュメント日: 2026-03-28

## [Unreleased]
（現時点で未リリースの項目はありません）

## [0.1.0] - 2026-03-28
初回公開リリース。以下の機能群と実装方針を含みます。

### Added
- パッケージ基盤
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"`、主要サブモジュールを `__all__` で公開（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動読み込み実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応。
    - コメント（#）の扱いに細かいルールを採用（クォート内は無視、クォート外は直前がスペース/タブの場合のみコメントとみなす）。
    - ファイル読み込み失敗時は警告を出して継続。
  - 設定アクセス用 `Settings` クラスを提供（`settings.jquants_refresh_token` など）。必須キー未設定時は `ValueError` を発生。
  - 環境値検証: `KABUSYS_ENV`（development/paper_trading/live）や `LOG_LEVEL` の妥当性チェックを実装。
  - DB パスのデフォルト (`DUCKDB_PATH`, `SQLITE_PATH`) を提供。
- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン (`kabusys.data.pipeline`)
    - 差分取得、バックフィル、品質チェックの実装方針を実装。
    - ETL 実行結果を表現する `ETLResult` dataclass を公開（`kabusys.data.etl` 経由で再エクスポート）。
    - デフォルトのバックフィル: 3 日。初回ロード用の最小データ開始日設定。
    - 品質チェックは問題を集約するが、重大度のある品質問題を検出しても ETL 自体は継続（呼び出し元で対処）。
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー同期ジョブ `calendar_update_job`（J-Quants からの差分取得、バックフィル 7 日、整合性チェック）。
    - 営業日判定ユーティリティ: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を実装。
    - カレンダー未取得時の曜日ベースフォールバック（週末は非営業日扱い）。DB 登録優先、未登録日はフォールバック。
    - 探索上限（最大日数）を設け無限ループを回避（デフォルト 60 日）。
- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`
    - モメンタム: `calc_momentum`（1M/3M/6M リターン、200 日 MA 乖離）。
    - ボラティリティ/流動性: `calc_volatility`（20 日 ATR、相対 ATR、平均売買代金、出来高比率）。
    - バリュー: `calc_value`（PER、ROE、raw_financials の最新報告データの参照）。
    - SQL を用いた DuckDB 内での実装（外部 API 呼び出しなし）。データ不足時は None を返す設計。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算: `calc_forward_returns`（複数 horizon をサポート、入力検証あり）。
    - IC（Information Coefficient）: `calc_ic`（スピアマンランク相関）。
    - ランク変換ユーティリティ: `rank`（同順位は平均ランク）。
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。
- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）に JSON モードでスコアリングして `ai_scores` に書き込み。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
  - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - 再試行（429、接続エラー、タイムアウト、5xx）を指数バックオフで実装（最大リトライ回数 3）。
  - レスポンス検証を厳格に実施（JSON パースの復元処理、"results" の型チェック、コード検証、数値チェック、スコアの ±1.0 クリップ）。
  - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は `ValueError` を送出。
  - フェイルセーフ: API 呼び出し失敗等で部分失敗しても他銘柄の既存スコアを消さないため、DELETE→INSERT をコード絞り込みで実行。
- AI 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合わせて日次で市場レジーム（bull/neutral/bear）を判定。
  - マクロニュースは raw_news からキーワード（日本・米国系のマクロ語彙）で抽出し、OpenAI に JSON 出力で評価を依頼。
  - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値でラベル化。
  - DuckDB の `market_regime` テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
  - OpenAI 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。API 呼び出しは独立実装でモジュール結合を避ける。
- 共通設計 / 実装方針
  - DuckDB を主要データストアとして使用。
  - ルックアヘッドバイアス回避: どの処理も内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date を基準に処理。
  - DB 書き込みは基本的に冪等化（DELETE→INSERT、ON CONFLICT 等）を意識。
  - OpenAI SDK 使用: chat.completions.create を JSON モード（response_format={"type": "json_object"}）で呼ぶ。temperature=0, timeout=30。
  - ロギングを随所に追加（情報・警告・例外の記録）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
- 実装上の堅牢性として以下を採用:
  - .env 読み込みでファイルアクセス失敗時に警告で回復。
  - DuckDB の executemany に空リストを渡すと失敗する点を考慮して空チェックを実装。
  - OpenAI レスポンスパース失敗や API 障害時は例外を直接上位に投げずフェイルセーフなデフォルト（0.0 など）を使用して処理継続。

### Security
- 明示的なセキュリティ修正はなし。ただし機密情報（OpenAI API キーや各種トークン）は環境変数経由で取得し、必須項目は明示的にチェックする実装を提供。

---

注意:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートでは実装済みのテスト状況、既知の問題、互換性の注記などを追加することを推奨します。