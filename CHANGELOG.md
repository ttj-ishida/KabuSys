# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

- 既知の初期リリース: 0.1.0

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。以下はコードベースから推測できる主要な追加・仕様です。

### 追加 (Added)
- パッケージ基盤
  - パッケージルート: `kabusys`（`__version__ = "0.1.0"`）。
  - 公開サブパッケージ: data, strategy, execution, monitoring のエクスポートを定義。

- 設定/環境変数管理 (`kabusys.config`)
  - .env ファイル自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 読み込み順序: OS環境変数 > .env.local > .env。自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - .env 行パーサーの実装（export プレフィックス、クォートやエスケープ、インラインコメントの扱いに対応）。
  - 環境変数取得ヘルパー `_require` と Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ化（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証（許容値チェック）。
    - is_live / is_paper / is_dev といった環境判定プロパティ。

- AI 関連 (`kabusys.ai`)
  - ニュースNLP スコアリング (`news_nlp.py`)
    - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント取得。
    - 時間ウィンドウ計算（前日15:00 JST 〜 当日08:30 JST を UTC に変換して使用）。
    - バッチ処理（最大 20 銘柄 / 回）、1銘柄あたりのトリム（記事数・文字数制限）。
    - レスポンス検証、JSON モードでのパース復元ロジック、スコアの ±1.0 クリップ。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データ保護）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321（日経225連動）の 200 日移動平均乖離 (重み 70%) と、マクロニュースの LLM センチメント (重み 30%) を合成してレジーム判定（bull/neutral/bear）。
    - DuckDB からの価格・ニュース取得、OpenAI 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームのスコア合成と冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止の設計（datetime.today() を直接参照しない、クエリに排他条件を使用）。

- データ基盤 (`kabusys.data`)
  - ETL インターフェース公開 (`etl.py` が pipeline.ETLResult を再エクスポート)。
  - ETL パイプライン (`pipeline.py`)
    - 差分更新、backfill、品質チェックの概念を実装する ETLResult（データクラス）を提供。
    - DuckDB の最大日付取得ユーティリティやテーブル存在チェック等を実装。
    - ETL の結果表現（品質問題・エラーの収集、辞書化サポート）。
  - マーケットカレンダー管理 (`calendar_management.py`)
    - JPX カレンダー取得・保存の夜間バッチ（calendar_update_job）。
    - 営業日判定・前後営業日の検索・期間内営業日取得・SQ 日判定等のユーティリティ。
    - DB データ優先、未取得日は曜日ベースのフォールバック、探索範囲制限（_MAX_SEARCH_DAYS）等の安全策。
    - J-Quants クライアント連携ポイント（jquants_client からの取得/保存呼び出しを想定）。

- リサーチ/ファクター解析 (`kabusys.research`)
  - ファクター計算（`factor_research.py`）
    - Momentum（1/3/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の計算関数を実装。
    - DuckDB SQL を活用した効率的な窓関数実装、欠損時の None 処理。
  - 特徴量探索/評価 (`feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman ランク相関）計算、rank 関数、統計サマリー（count/mean/std/min/max/median）。
    - pandas 等の外部依存を使わず標準ライブラリで実装。

### 変更 (Changed)
- （初回リリースのため「変更」項目は該当なし。ただし内部設計上の方針や実装上の注意点をドキュメント内に反映）
  - 各モジュールで「ルックアヘッドバイアス防止」「DuckDB バージョン互換性（executemany の空リスト回避等）」を設計方針として明示。

### 修正 (Fixed)
- OpenAI / API 呼び出し周りの堅牢化
  - JSON パース失敗時の復元処理、API エラー種別ごとの扱い（429/ネットワーク/タイムアウト/5xx のリトライ、その他はフォールバック）。
  - 例外発生時の DB トランザクションの ROLLBACK 保護（ROLLBACK に失敗した場合は警告ログを出力）。

### セキュリティ (Security)
- 環境変数の保護
  - .env 自動ロード時、OS 環境変数を保護（読み込み時に既存の os.environ キーを protected set として扱う）。
  - API キーの取得は明示的（引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）。未指定時は ValueError を発生させる。

### 注意事項 / 実装上の設計ノート
- ルックアヘッドバイアス防止: ほとんどの処理が target_date ベースで動作し、datetime.today() を直接参照しない設計。
- DuckDB 互換性: executemany に空リストを渡さない等、特定 DuckDB バージョン（例: 0.10）への注意喚起を含む実装。
- 冪等性: calendar や ai_scores 等の DB 書き込みは既存行を上書きする／置換する形で実装されている（DELETE→INSERT や ON CONFLICT を想定）。
- テスト容易性: OpenAI への呼び出しをラップした内部関数を patch して差し替え可能にしている（ユニットテストでの API 呼び出し抑止を想定）。
- エラーのフォールバック方針: 外部 API の失敗は可能な限りフェイルセーフ（スコアを 0 にする、処理をスキップして継続等）で扱う。

---

今後のリリースに向けて想定される追加事項（参考）
- strategy / execution / monitoring の具体的実装（現状はエクスポート宣言のみ）。
- 追加の品質チェックルールやアラート機能（Slack 通知連携等）。
- DuckDB スキーマ定義・マイグレーション機能、ロギング/メトリクスの整備。
- テストカバレッジ向上・CI 設定の明示。

---

（注）本 CHANGELOG は提示されたソースコードから機能・設計意図を推測して作成したものです。実際のコミット履歴や履歴管理方針に合わせて適宜調整してください。