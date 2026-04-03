# Changelog

すべての変更は「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。  
このファイルはコードベースから推測して作成した初回リリースの変更履歴です。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 初回リリース: KabuSys — 日本株自動売買システムの基盤機能を提供。
- パッケージ公開:
  - パッケージルート: `kabusys`（__version__ = 0.1.0）。
  - 主要サブパッケージをエクスポート: `data`, `strategy`, `execution`, `monitoring`（公開インターフェースの準備）。

- 環境設定・設定管理 (`kabusys.config`):
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env/.env.local の優先順位制御（`.env.local` が上書き、OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - `.env` パースの強化:
    - `export KEY=val` 形式に対応。
    - シングル・ダブルクォート内でのバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート外かつ直前がスペース/タブの `#` をコメントとする）。
  - 必須環境変数取得の `_require`、設定を提供する `Settings` クラス（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境判定などのプロパティ）。

- データプラットフォーム（`kabusys.data`）:
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダー取得・更新バッチ（calendar_update_job）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB にデータがない場合の曜日ベースフォールバック実装。
    - 最大探索日数やバックフィル、健全性チェックを実装。
  - ETL パイプライン (`pipeline`):
    - ETL 実行結果を表す `ETLResult` dataclass（品質チェック結果・エラー情報含む）。
    - 差分更新、バックフィルポリシー、品質チェック方針を想定した設計（J-Quants クライアント経由の取得・保存を前提）。
  - ETL 公開インターフェース `kabusys.data.etl` で `ETLResult` を再エクスポート。

- 研究・ファクター解析（`kabusys.research`）:
  - ファクター計算 (`factor_research`):
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER（price / EPS、EPS=0/欠損時は None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQL+ウィンドウ関数ベースの実装、データ不足時は None を返す設計。
  - 特徴量探索 (`feature_exploration`):
    - 将来リターン計算: `calc_forward_returns`（horizons に応じた fwd_* 計算）。
    - IC（Information Coefficient）計算: `calc_ic`（スピアマンのランク相関）。
    - ランク関数: `rank`（同順位は平均ランク、丸めによる ties 対応）。
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）。
  - 研究ユーティリティの再エクスポート: `zscore_normalize`（`kabusys.data.stats` 由来）など。

- AI / NLP 機能（`kabusys.ai`）:
  - ニュースセンチメントスコアリング: `news_nlp.score_news`
    - raw_news + news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、記事数・文字数の上限、JSON Mode を利用したレスポンス処理。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフで再試行）。
    - レスポンスの厳密なバリデーション（results 配列、各要素 code/score、スコアは数値かつ有限、不正レスポンスは安全にスキップ）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE→INSERT）。
    - テスト容易性のため OpenAI 呼び出しをパッチ可能に設計（_call_openai_api）。
  - 市場レジーム判定: `regime_detector.score_regime`
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジームを判定（bull/neutral/bear）。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（JSON レスポンス）、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア計算、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しのリトライ・エラーハンドリングを備える。

- 依存・実装方針（ドキュメント的情報）
  - DuckDB を主要なローカル DB として利用する設計（DuckDB 接続オブジェクトを各関数で受け取る）。
  - ルックアヘッドバイアス防止: 直接 datetime.today()/date.today() を参照しない実装方針（関数は target_date を明示的に受け取る）。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT 想定など）。
  - エラー時はフェイルセーフで継続する設計（部分失敗や API エラーでシステム全体を停止させない）。
  - ロギングを適切に挿入（info/debug/warning/exception）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- 本 CHANGELOG はソースコードの実装とドキュメント文字列から推測して作成したものであり、実際のリリースノートはプロジェクトのリリース担当者により追加・修正される可能性があります。