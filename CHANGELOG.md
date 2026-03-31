# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
安定版・互換性の判断はセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買 / 研究 / データ基盤のコア機能を実装。

### 追加 (Added)
- パッケージの公開バージョンを定義
  - `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動読み込み機能を実装（プロジェクトルート検出は `.git` または `pyproject.toml` を基準）。
  - 読み込み優先度: OS環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` のパースで `export KEY=val`、引用符内のバックスラッシュエスケープ、行内コメント処理などをサポート。
  - `Settings` クラスを追加し、主要設定プロパティを提供:
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development / paper_trading / live）/ ログレベル等。
  - 必須環境変数未設定時は `_require` が `ValueError` を送出。

- AI / ニュース NLP (`kabusys.ai.news_nlp`)
  - ニュース記事を銘柄ごとに集約して LLM (gpt-4o-mini) に JSON Mode で投げ、銘柄別センチメント（-1.0〜1.0）を計算して `ai_scores` テーブルに書き込む処理 `score_news(conn, target_date, api_key=None)` を実装。
  - 時刻ウィンドウ計算ユーティリティ `calc_news_window(target_date)` を実装（JST ベース → DB 用 UTC naive）。
  - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数上限、JSON レスポンスの堅牢なバリデーションを実装。
  - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を指数バックオフで再試行。致命的な API エラーは該当チャンクをスキップして継続するフェイルセーフ設計。
  - DuckDB の互換性考慮（`executemany` に空リストを渡さない等）で、部分失敗時にも既存スコアを保護する置換ロジック（DELETE → INSERT）を採用。
  - テスト容易性のため、OpenAI 呼び出しを `_call_openai_api` に抽象化（テスト時に patch 可能）。

- AI / 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
  - prices_daily からの MA200 比率計算、raw_news からマクロキーワード一致のタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）でセンチメント算出、スコア合成、`market_regime` テーブルへの冪等書き込みまでを一連で実行。
  - OpenAI API 呼び出しでのリトライ、API失敗時のフォールバック（macro_sentiment=0.0）を実装し、例外を最小化する設計。
  - モジュール間の結合を抑えるため、LLM 呼び出しは独自実装（news_nlp と共用しない）。

- データ基盤（Data）モジュール
  - ETL パイプライン (`kabusys.data.pipeline`)
    - 差分更新、バックフィル、品質チェックのための基盤となる `ETLResult` データクラスを実装（取得数・保存数・品質問題・エラー情報を格納）。
    - DuckDB のメタ情報取得ユーティリティ（テーブル存在確認、最大日付取得）を追加。
    - 市場カレンダー補正・調整ユーティリティ（営業日調整など）の内部関数を実装。
  - ETL 再エクスポート
    - `kabusys.data.etl` で `ETLResult` を公開。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間差分更新バッチ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants クライアント経由で取得、冪等保存）。
    - 営業日判定ロジック: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。
    - DB のカレンダー情報がない場合は曜日ベースでフォールバックする堅牢な挙動。
    - 健全性チェック・バックフィル・最大探索日数制限を実装。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）などの計算関数を実装:
      - `calc_momentum(conn, target_date)`
      - `calc_volatility(conn, target_date)`
      - `calc_value(conn, target_date)`
    - DuckDB SQL ベースでの計算を行い、(date, code) キーの dict リストを返却する設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21]）を実装。
    - IC（Information Coefficient）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)` を実装（スピアマンρ、有効データが不足する場合は None を返す）。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク）と、統計サマリー `factor_summary(records, columns)` を実装。
  - 研究用ユーティリティを `__all__` で公開。

- その他
  - パッケージ内モジュールの public API を `__all__` で整理（例: `kabusys.ai.__all__ = ["score_news"]` 等）。
  - OpenAI クライアント呼び出しは `OpenAI(api_key=...)` を使用する実装に統一。

### 変更 (Changed)
- 初回リリースのため過去バージョンからの変更はなし。

### 修正 (Fixed)
- OpenAI 結果の JSON パースにおいて余分な前後テキストが混入する場合に対応する復元ロジックを実装（最外の `{...}` を抽出してパースを試行）。
- DuckDB に対するバインド/execu temany の挙動（空リストの扱い）を考慮した実装で、部分失敗時に既存データを不用意に消去しないよう保護。

### 注意事項 / 既知の制約 (Note / Known limitations)
- OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定する必要がある。未設定時は `ValueError` を送出する。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。パッケージ配布後やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- AI モジュールは外部 API (OpenAI) に依存するため、レイテンシや料金、API 利用制限に注意すること。
- DuckDB による SQL 実行の性質上、日付型の取り扱いやバインドの互換性に注意（実装内で互換性対策あり）。
- 全モジュールで「ルックアヘッドバイアス防止」の設計方針を採用しているため、内部で datetime.today() / date.today() を直接参照する処理は避けられている。スコア算出は呼び出し元が明示的に target_date を渡すことを想定。

### セキュリティ (Security)
- 環境変数からトークンやパスワードを読み込む実装のため、`.env` ファイルや環境変数の管理に注意すること（機密情報は適切に保護すること）。

---

記載した API 名、関数、動作はソースコードを基に推測しています。追加の変更履歴（バグ修正や機能追加）がある場合は、差分を提供いただければ対応するバージョン/項目を追記します。