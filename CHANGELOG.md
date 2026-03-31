# CHANGELOG

本プロジェクトは Keep a Changelog の形式に準拠して変更履歴を管理します。  
このファイルは、コードベース（src/kabusys 以下）の内容から推測して作成した初期リリース向けの変更履歴です。

すべての重要な変更はここに記載します。  

## [0.1.0] - 2026-03-31

最初の公開バージョン。以下の主要機能と実装が追加されました。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - パッケージの公開モジュールを __all__ で指定（data, strategy, execution, monitoring）。
- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動 .env 読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは以下の挙動に対応：
    - コメント行・空行の無視
    - `export KEY=val` 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし値内のインラインコメント処理（直前が空白/タブの場合のみ）
  - Settings クラスを提供し、アプリケーションで使用する主要設定をプロパティで取得可能：
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル 等
  - 必須環境変数未設定時には ValueError を発生させる `_require` を採用。
- AI（自然言語処理）モジュール
  - `kabusys.ai.news_nlp`:
    - raw_news および news_symbols をソースとして銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを評価。
    - バッチ処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数のトリム、API レート制限やネットワーク障害への指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー・型チェック、未知コード無視、数値変換、有限性チェック）。
    - スコアは ±1.0 にクリップ。取得成功銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT）。DuckDB の executemany 空リスト制約に配慮。
    - テスト容易性のため OpenAI 呼び出し関数を patch できるよう設計。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225 連動）を用いた 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照して ma200_ratio を算出、ニュースは `news_nlp.calc_news_window` のウィンドウで抽出し OpenAI で評価。
    - API 呼び出しはリトライ実装、API 失敗時は macro_sentiment を 0.0 にフォールバックしてフェイルセーフ動作。
    - 判定結果は market_regime テーブルに冪等で書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK と例外伝播。
- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算（`factor_research.py`）:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を提供。
    - データ不足時は None を返す設計。結果は (date, code) キーを持つ dict のリストで返却。
  - 特徴量探索（`feature_exploration.py`）:
    - 将来リターン計算（任意 horizon、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - zscore_normalize を data.stats から再エクスポート（research パッケージの __init__ にて）。
- データプラットフォーム（Data）モジュール
  - カレンダー管理（`data.calendar_management`）:
    - JPX カレンダーの扱い（market_calendar テーブル）と、営業日判定・next/prev_trading_day・get_trading_days・is_sq_day のロジックを提供。
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックが働くように設計。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・冪等保存（バックフィルと健全性チェックあり）。
  - ETL パイプライン（`data.pipeline` / `data.etl`）:
    - ETLResult データクラスを追加（取得件数・保存件数・品質検査結果・エラーリスト等を保持）。
    - 差分取得・保存・品質チェックの処理フローを実装する土台を提供。
    - jquants_client と quality モジュールを橋渡しする設計（差分更新、backfill、部分書き換え保護など）。
  - その他ユーティリティ:
    - テーブル存在チェック、最大日付取得などのユーティリティを提供（DuckDB 互換を考慮）。
- ドキュメント的コメント（モジュール docstring）
  - 多くのモジュールで処理フロー・設計方針・フェイルセーフ挙動・テストフック等を明示した docstring を追加。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### セキュリティ (Security)
- 特になし。ただし OpenAI API キーや各種トークンは Settings を通じて環境変数で管理する設計になっており、設定漏洩には注意が必要。

### 実装上の注記（重要）
- OpenAI 関連
  - gpt-4o-mini（_MODEL）をデフォルトで使用。JSON モードでの出力を前提とするため、厳密な JSON を期待するプロンプトを採用しているが、レスポンスの前後に余計なテキストが混在する場合を考慮して JSON 抽出ロジックも備えている。
  - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフのリトライを実装。API エラーはフェイルセーフとして 0.0 スコアやスキップで継続する設計。
  - テスト容易性のため、OpenAI 呼び出し点はモジュール内で関数化しており patch で差し替え可能。
- ルックアヘッドバイアス対策
  - ほとんどの時刻関連処理で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を明示的に渡す設計。DB クエリも target_date 未満／以前のデータのみ参照することで将来情報漏洩を防ぐ。
- DB トランザクションと互換性
  - 主要な DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン、異常時は ROLLBACK を試行して例外を上位へ伝播。
  - DuckDB の executemany における空リストの制約に注意し、空の場合は呼び出しをスキップする防御的実装あり。
- 設定の自動ロード
  - .env の自動読み込みは実行時の OS 環境変数を保護する仕組み（protected set）を導入。`.env.local` は既存環境変数を上書きできる仕様。
- エッジケース
  - データ不足（移動平均のサンプル不足など）や API 失敗時にはログに警告を出しつつ中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）を用いるなど、安全優先の取り扱いを行う。

### 既知の制約・今後の改善ポイント（推奨）
- ETL / pipeline の一部ユーティリティや jquants_client / quality モジュールは外部実装に依存するため、これらの実装によって挙動が左右される。
- モデルやバッチサイズ、ウィンドウ定義などは定数としてハードコードされている（将来的に設定化を検討）。
- OpenAI のモデル API 仕様変更に備え、例外処理の網羅やレスポンスパースの冗長性をさらに強化する余地あり。
- ドキュメント（Usage / API / CLI）が限られているため、利用者向けの README やサンプルコードを追加することが望ましい。

---

この CHANGELOG はコードベースを解析して推測した内容に基づいて作成しています。実際のリリースノートとして使用する場合は、実装状況や変更履歴に応じて適宜編集してください。