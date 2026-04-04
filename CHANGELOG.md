# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ初期リリース。
- 基本パッケージ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含む。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサの実装（コメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを考慮）。
  - .env 読み込み時の上書き制御（override / protected）をサポート。
  - Settings クラスを提供（環境変数経由で各種設定を取得）:
    - J-Quants / kabu API / LINE トークン等の設定取得プロパティ
    - データベースパス（DuckDB / SQLite）、監視関連ファイルパス、リソース閾値（CPU/メモリ/ディスク）
    - 環境 (`KABUSYS_ENV`: development / paper_trading / live) とログレベル検証（DEBUG/INFO/...）
    - is_live / is_paper / is_dev のブール判定プロパティ
  - 必須環境変数未設定時にわかりやすい例外を投げる `_require` 実装。

- AI 関連機能 (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
    - タイムウィンドウ定義（JST: 前日15:00〜当日08:30 → UTC に変換）を `calc_news_window` で提供。
    - 銘柄ごとに最大記事数 / 文字数でトリムし、最大バッチサイズ（20銘柄）で API へ送信。
    - JSON Mode 応答のパースと堅牢なバリデーション（余分な前後テキストの復元ロジック含む）。
    - レート制限・接続障害・タイムアウト・5xx に対する指数バックオフの再試行ロジック。
    - スコアを ±1.0 にクリップし、取得済みコードのみ ai_scores テーブルへ置換的に書き込む（DELETE → INSERT、部分失敗時に他コードを保護）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（内部関数に分離）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動）の 200日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を決定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロ記事抽出はキーワードベース（リストで定義）で最大 20 件を対象、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 で継続。
    - OpenAI 呼び出しは `OpenAI(api_key=...)` を用い、失敗時はフェイルセーフ（0.0）で継続。リトライ/バックオフ実装あり。
    - 計算結果（regime_score, regime_label, ma200_ratio, macro_sentiment）を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行し例外伝播。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar テーブルの存在チェック、営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダー登録がない場合は曜日ベースでフォールバック（土日を休日扱い）。
    - 夜間バッチジョブ `calendar_update_job`（J-Quants から差分取得 → 保存、バックフィル・健全性チェック機能内蔵）。
    - 最大探索日数、ルックアヘッド、バックフィル日数などの安全パラメータを設定。
  - ETL パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETL 実行結果を表す `ETLResult` dataclass を公開。
    - 差分更新、保存（idempotent な保存を想定）、品質チェックフレームワークとの連携方針を実装。
    - デフォルトのバックフィル日数、カレンダールックアヘッド等を定義。

- リサーチ／ファクター関連 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: 約1ヶ月／3ヶ月／6ヶ月リターン、200日MA乖離（ma200_dev）。
    - Volatility / Liquidity: 20日ATR、ATR比率、20日平均売買代金、出来高比率等。
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から最新報告を使用）。
    - 各計算は DuckDB 上で SQL と Python を組み合わせて実行。欠損やデータ不足時の安全な None 処理。
  - 特徴量解析 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）について fwd_xd を計算。horizons の妥当性チェックあり。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関を実装し、データ不足時には None を返す。
    - ランク関数（rank）: 同順位は平均ランクで処理、浮動小数誤差を抑えるため round を使用。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key 引数）で、環境変数 OPENAI_API_KEY をフォールバック。キー管理の柔軟性を提供。

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス対策: AI モジュール、ファクター計算、ETL ジョブいずれも内部で datetime.today() / date.today() を直接参照せず、明示的に target_date を受け取る設計。
- フェイルセーフ: 外部 API 呼び出しやパース失敗時は例外を安易に投げずデフォルト値（0.0 や None）で継続する実装方針を採用。ただし DB 書き込み失敗はロールバック後に上位へ伝播。
- テスト容易性: OpenAI 呼び出しや内部の I/O 部分は差し替え可能に実装（ユニットテストでの patch を想定）。
- DuckDB を中心としたローカルデータ管理、SQL ウィンドウ関数や executemany の互換性考慮など、実運用での安定性を重視。

（以降のバージョンでは追加機能、バグ修正、パフォーマンス改善等をこの changelog に追記します）