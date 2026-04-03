# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

未リリースの変更は [Unreleased] に記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買/データ基盤・研究・AI支援分析の基礎機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 `kabusys` を導入。バージョンは `0.1.0`。
  - パッケージの公開インターフェースに `data`, `strategy`, `execution`, `monitoring` を登録（__init__.py）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル（`.env` / `.env.local`）および OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない動作を実現。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（`#`）の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しでのインラインコメント判定（直前が空白/タブの場合）
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - 必須環境変数取得用 `_require`、および `Settings` クラスを提供。`JQUANTS_REFRESH_TOKEN`、`KABU_API_PASSWORD`、`OPENAI_API_KEY` 等の利用が想定される。
  - 各種デフォルト値と型変換を備えたプロパティ（DBパス、PID/KILLファイルパス、閾値、環境モードの検証、ログレベル検証など）。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング（`score_news`）
    - raw_news / news_symbols をまとめて銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/コール）、各銘柄ごとに最新 N 件・文字数トリム（最大 10 記事・3000 文字）を実装。
    - JSON Mode を利用し、レスポンスのバリデーションとスコアの ±1.0 クリップを実施。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ）。
    - DuckDB へ idempotent に書き込む（DELETE → INSERT、トランザクション、部分失敗時の保護）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（内部関数にラップ）。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（`score_regime`）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - raw_news からマクロキーワードでフィルタし、OpenAI でマクロセンチメントを取得。
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0。
    - レジーム結果を `market_regime` テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

  - 共通設計方針:
    - LLM 呼び出しは独立実装としテストで簡単にモック可能にしている。
    - どちらのモジュールも datetime.today()/date.today() を直接参照せず、引数の target_date に依存してルックアヘッドバイアスを排除。

- データ基盤 (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - JPX カレンダーを扱うユーティリティ群を実装：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB（market_calendar）優先の判定ロジックと、データ不在時の曜日ベースのフォールバックを一貫して実装。
    - calendar_update_job: J-Quants クライアント経由で差分取得・バックフィル・保存を行う夜間バッチ処理を実装。健全性チェック（遠すぎる last_date のスキップ等）を備える。
    - 内部で DuckDB の日付型変換ユーティリティやテーブル存在チェックなどを実装。

  - ETL パイプライン (`pipeline.py`) と ETL 結果 (`etl.py`)
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラーリスト等を格納）。
    - 差分更新、backfill、品質チェック（quality モジュールと連携）を想定した設計。
    - jquants_client との連携を前提とした差分取得・保存フロー設計を実装。

- リサーチ/ファクター (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（calc_momentum）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（calc_volatility）。
    - Value: PER（price / EPS）、ROE を raw_financials と prices_daily から計算（calc_value）。
    - すべて DuckDB 上で SQL を主体に計算し、本番口座/発注 API へは接触しない設計。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値からリターンを算出。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関による評価を実装。
    - ランキングユーティリティ（rank）、ファクター統計サマリー（factor_summary）を提供。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)
- 初版リリースにあたって、各モジュールは「設計方針」を守った実装となっている（ルックアヘッドバイアス回避、DB の冪等性、フェイルセーフの明示など）。

### 修正 (Fixed)
- 初期実装のため既知のバグ修正履歴はなし（今後の運用で検出次第追加予定）。

### 注意点 / 実装上の制約
- OpenAI API を利用する箇所は環境変数 `OPENAI_API_KEY` または関数引数での注入が必要。
- DuckDB によるバインド/execute/ executemany の挙動（空リストでの executemany 非対応等）を考慮している。
- JSON Mode を使うが、稀に前後テキストが混入する場合に備えた復元ロジックを実装している（レスポンスパース失敗時は安全にスキップし、スコアは取得失敗扱いとなる）。
- calendar_update_job 等は外部 J-Quants クライアント（kabusys.data.jquants_client）実装を前提としている。

---

（本 CHANGELOG はコードリポジトリの現状ファイル群から機能と設計を推測して作成しています。実際のリリースノートや運用方針の変更がある場合は適宜更新してください。）