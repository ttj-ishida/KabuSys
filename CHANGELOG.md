# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased

## [Unreleased]

- （今後の変更をここに記載してください）

## [0.1.0] - 2026-04-01

初期公開リリース。

### 追加 (Added)

- パッケージ初期構成
  - パッケージメタ: `kabusys.__init__` にバージョン "0.1.0" と公開モジュール一覧を追加。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装
    - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に実施（CWD非依存）。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサ実装（`export KEY=val`、クォート／エスケープ、インラインコメント扱いに対応）。
  - 上書き動作と保護キー（OS環境変数の保護）をサポートする読み込み関数。
  - 必須環境変数チェック（`_require`）と Settings クラスを提供：
    - J-Quants / kabuステーション / Slack / DB パス / 監視設定 / システム設定（env, log_level）等のプロパティを用意。
    - `env` と `log_level` の妥当性チェック（許容値制約）。
    - Path 型や float 型への変換を実装。

- AI モジュール
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - 指定タイムウィンドウの raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して `ai_scores` テーブルへ書き込み。
    - チャンク処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、JSON Mode を利用したレスポンス検証実装。
    - 再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（API失敗時は該当チャンクをスキップして継続）。
    - レスポンス検証ロジック（JSON 抽出、results リスト、コード検証、スコア数値検証、±1.0 クリップ）を実装。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出（キーワードベース、最大 20 件）→ OpenAI（gpt-4o-mini）呼び出し→ JSON パース→ スコア合成。
    - API リトライ（指数バックオフ）、API 異常時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

  - 共通設計方針（AI系両モジュール）
    - OpenAI 呼び出しはモジュール内で独立実装（モジュール間で private 関数を共有しない設計）。
    - テスト容易性のため OpenAI 呼び出し関数は置き換え（patch）可能に設計。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照せず、明示的な target_date を使用。

- データモジュール (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダー管理ロジック（market_calendar の参照・更新、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日とする）。
    - 最大探索日数制限や健全性チェック、バックフィルの考慮を実装。
    - 夜間バッチ更新ジョブ（`calendar_update_job`）: J-Quants から差分取得し保存・バックフィルを行う処理を実装。

  - ETL パイプライン (`pipeline`, `etl` 再エクスポート)
    - ETL の結果を表す dataclass `ETLResult` を提供（取得数・保存数・品質問題・エラー一覧など）。
    - 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client 経由）を行う ETL 方針を実装（pipeline 内にユーティリティ）。
    - DuckDB の存在確認や最大日付取得などの内部ユーティリティを実装。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB SQL ウィンドウ関数を活用した実装、データ不足時の None 扱い。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（任意ホライズン、入力検証）、IC（Spearman ランク相関）計算、ランク関数（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティの公開と再エクスポート（`zscore_normalize` は data.stats から再利用）。

### 変更 (Changed)

- （初期リリースのため該当なし）

### 修正 (Fixed)

- （初期リリースのため該当なし）

### セキュリティ (Security)

- （初期リリースのため該当なし）

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス防止: すべての分析/スコアリング関数は明示的な target_date を使用し、内部で現在時刻を暗黙的に参照しない設計。
- DB 書き込みは冪等化（DELETE→INSERT 等）し、失敗時はトランザクションでロールバックを試みる。
- OpenAI 呼び出しは JSON Mode を使う想定とし、レスポンスの堅牢な検証処理を実装。
- フェイルセーフ: API 失敗やデータ不足時に処理全体が停止しないよう、部分スキップやデフォルト値（中立スコアなど）を用いる。

---

参考: バージョンはパッケージ内 `src/kabusys/__init__.py` の `__version__` に合わせて付与しています。今後の変更は Unreleased に記載し、リリースごとにバージョンと日付を記述してください。