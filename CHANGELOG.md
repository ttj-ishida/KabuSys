# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用しています。

## [Unreleased]

（現状のソースはバージョン 0.1.0 としてリリース済みの想定です。今後の変更はここに記載します。）

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買 / 研究 / データ基盤のためのコアライブラリ群を提供します。主な追加点・設計方針・既知の制約は以下の通りです。

### 追加 (Added)
- パッケージ基本
  - `kabusys` パッケージの初期公開。
  - バージョン情報 `__version__ = "0.1.0"` を追加。
  - パッケージ公開インターフェースに `data`, `strategy`, `execution`, `monitoring` を登録。

- 設定管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準とした .env 自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
    - `.env` パーサは `export KEY=val` 形式、引用符付き文字列、エスケープ、行末コメントの扱いなどを考慮。
    - `.env` 読み込み時に OS 環境変数を保護する `protected` 挙動（`.env` 上書き防止）を実装。
  - `Settings` クラスを追加し、以下の設定プロパティを提供:
    - J-Quants / kabu ステーション / LINE / DB パス（DuckDB / SQLite） / 監視用 PID/KILL フラグ / リソース閾値 / 環境 (development, paper_trading, live) / ログレベル など。
    - 必須環境変数未設定時は明示的な `ValueError` を送出する `_require` を採用。
    - `env` / `log_level` の値検証を実装（許容値外は例外）。

- AI（NLP）関連
  - `kabusys.ai.news_nlp`
    - ニュース記事（`raw_news`）を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - 特徴:
      - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）、DB 比較は UTC naive datetime で実装（ルックアヘッド防止）。
      - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE=20）、1銘柄あたり最大 10 記事、最大 3000 文字にトリム。
      - JSON Mode での厳格な JSON 出力を期待しつつ、前後ノイズ混入に備え最外の {} を抽出して復元するフォールバック処理を実装。
      - リトライ: 429 / 接続エラー / タイムアウト / 5xx に対して指数バックオフでリトライ（最大回数制御）。
      - レスポンスのバリデーション（results 配列・各要素の code/score 等）、スコアを ±1.0 にクリップ。
      - DuckDB 互換性を考慮し、空パラメータでの executemany を回避する実装（部分失敗でも既存データを保護）。
    - パブリック API: `score_news(conn, target_date, api_key=None)` は書込み銘柄数を返す。API キー未設定時は `ValueError`。

  - `kabusys.ai.regime_detector`
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を計算。
    - 特徴:
      - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
      - マクロニュースは `raw_news` からマクロキーワードでフィルタしてタイトルを抽出（最大 20 記事）。
      - OpenAI 呼び出しは専用実装で、API 失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
      - 結果は `market_regime` テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み。
    - パブリック API: `score_regime(conn, target_date, api_key=None)` は成功時に 1 を返す。API キー未設定時は `ValueError`。

- データ（Data platform）
  - `kabusys.data.pipeline` / `kabusys.data.etl` を追加。
    - ETL 結果を表す `ETLResult` dataclass を公開（`etl.ETLResult` を `data` パッケージで再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を想定した冪等保存）、品質チェック（`quality` モジュール連携）を想定した設計ドキュメントに準拠。
    - ETLResult は品質問題を構造化して `to_dict()` で出力可能。
    - 一部定数: 初期データ開始日、バックフィル日数、カレンダー先読みなどを定義。

  - `kabusys.data.calendar_management`
    - JPX カレンダー管理（`market_calendar` テーブル）のユーティリティを実装。
    - 提供関数:
      - is_trading_day(conn, d)
      - is_sq_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
      - calendar_update_job(conn, lookahead_days=...)
    - 挙動:
      - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック。
      - DB 登録があれば DB 値優先、未登録日は曜日フォールバックで一貫性を保つ。
      - 夜間バッチ `calendar_update_job` は J-Quants クライアントを呼び出して差分取得・保存（バックフィル・健全性チェック付き）。
      - 最大探索範囲やバックフィル、lookahead のデフォルト値は定義済み（安全装置あり）。

- リサーチ（Research）
  - `kabusys.research.factor_research`
    - ファクター計算機能を実装（prices_daily / raw_financials を参照する設計）。
    - 提供関数:
      - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）
      - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio（データ不足時は None）
      - calc_value(conn, target_date): per / roe（EPS が 0/欠損の場合は None、PBR/配当未実装）
    - DuckDB SQL を活用した高効率なウィンドウ集計実装。
  - `kabusys.research.feature_exploration`
    - 研究ユーティリティ（外部依存なしで実装）
    - 提供関数:
      - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を一度のクエリで取得
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）IC 計算（ties 平均ランクを採用）
      - rank(values): 平均ランク方式（同値は round(v,12) による丸めを利用）
      - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリー

### 変更点・設計方針 (Changed / Design decisions)
- ルックアヘッドバイアス防止:
  - AI・レジーム判定・ファクター計算・ニュースウィンドウ等、すべて target_date を外部入力として受け取り、内部で datetime.today()/date.today() を参照しない実装に統一。
- フェイルセーフ設計:
  - 外部 API（OpenAI / J-Quants 等）の失敗時は可能な限りスキップやデフォルト値（例: macro_sentiment=0.0）で継続し、致命的な例外は上位へ伝播する方針。
- DuckDB 互換性:
  - DuckDB の executemany に関する制約（空リスト不可）を回避するため、空の場合は実行をスキップするチェックを導入。
- OpenAI 呼び出し:
  - モジュール間の結合を避けるため、`news_nlp` と `regime_detector` でそれぞれ独立した `_call_openai_api` 実装を提供。単体テスト容易性のためモック差し替えを想定（ユニットテストでの patch を想定）。

### 修正 (Fixed)
（この初回リリースではバグ修正履歴はなし。実装上の注意点や回避策は設計方針に記載。）

### 既知の制約・未実装 (Known issues / Not implemented)
- `calc_value` では現時点で PBR・配当利回りは未実装。
- `strategy`, `execution`, `monitoring` の詳細実装はこのリリースの範囲外（パッケージ階層は存在するがモジュール内容は本リリースに含まれない可能性あり）。
- OpenAI の JSON レスポンスが完全に期待通りでないケースに備えたフォールバックは入れているが、LLM 出力の多様性に完全には対応できない場合がある。
- calendar_update_job 等は J-Quants クライアント (`kabusys.data.jquants_client`) に依存しており、外部 API の変更や認証周りで追加対応が必要になる可能性がある。

### セキュリティ (Security)
- 環境変数の扱いに関して、.env の自動ロードはデフォルトで有効だが、テストや安全性のために `KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。
- OpenAI / 外部 API キーの扱いは環境変数経由を想定。必須未設定時は明示的なエラーを出す実装。

---

今後のリリースでは以下を想定しています（例）:
- strategy / execution / monitoring の具体実装および統合テスト
- J-Quants クライアントの拡充とリトライ/認証強化
- PBR・配当利回りなどバリューファクターの拡張
- CI 用のモック / テストヘルパー整備（OpenAI / DuckDB のモック等）

（必要であれば、この CHANGELOG を英語版に翻訳したり、リリースノートを拡張します。）