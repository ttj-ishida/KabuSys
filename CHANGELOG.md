# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]
- 今後のリリースへ向けた変更点はここに記載します。

## [0.1.0] - 2026-04-03
初期公開リリース

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理 (`kabusys.config`)
  - .env / .env.local ファイルおよび OS 環境変数からの自動ロード機能を実装
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
    - `.env.local` は `.env` 上書き（ただし既存の OS 環境変数は保護）
    - 不正な .env 行のパース、クォート・エスケープ・インラインコメントの取り扱いを実装
  - Settings クラスを提供（プロパティ経由で各種設定を取得）
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル / 環境種別 等
    - env 値・log_level のバリデーション（有効値集合チェック）
    - is_live / is_paper / is_dev のユーティリティ

- AI モジュール (`kabusys.ai`)
  - news_nlp モジュール
    - raw_news から銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価
    - バッチング（最大20銘柄/コール）、記事・文字数トリム、JSON パースとレスポンス検証を実装
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ実装
    - スコアのクリップ（±1.0）と ai_scores テーブルへの冪等書き込み（DELETE → INSERT）
    - テスト容易性のため _call_openai_api をパッチ差し替え可能
    - calc_news_window ユーティリティ（JST ウィンドウ → UTC naive datetime 変換）
  - regime_detector モジュール
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成し
      市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み
    - LLM 呼び出しのエラーハンドリング（フェイルセーフで macro_sentiment=0.0 にフォールバック）
    - _calc_ma200_ratio, _fetch_macro_news, _score_macro 等の分割実装
    - _call_openai_api は news_nlp と意図的に別実装（モジュール間の結合を回避）

- データモジュール (`kabusys.data`)
  - calendar_management
    - JPX カレンダー管理ロジックを実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - market_calendar テーブルがない場合は曜日ベースでフォールバック（週末を休場扱い）
      - DB の登録値優先・未登録日は曜日フォールバック、最大探索範囲の保護実装
    - calendar_update_job: J-Quants からの差分取得・バックフィル・保存処理を実装（健全性チェック付き）
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化）
    - ETL モジュールの骨組み（差分取得、保存、品質チェックの呼び出し方針、バックフィル等）を実装
    - DuckDB を前提としたテーブル存在チェック・最大日付取得ユーティリティ等を提供
  - etl の公開インターフェース（ETLResult を再エクスポート）

- Research モジュール (`kabusys.research`)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標、バリュー（PER/ROE）等の計算関数を実装
    - DuckDB 上の SQL とウィンドウ関数を用いて高速に計算
    - データ不足時の None 扱い、結果は (date, code) を含む dict のリストで返却
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティを実装
    - pandas 等に依存せず標準ライブラリと DuckDB SQL のみで実装

### 変更 (Changed)
- 該当なし（初期リリース）

### 修正 (Fixed)
- 該当なし（初期リリース）

### 注意事項 / 実装上の設計上のポイント
- ルックアヘッドバイアス回避
  - 全ての AI / リサーチ処理は内部で datetime.today() / date.today() を直接参照せず、呼び出し元から target_date を受け取る設計
  - DB クエリは target_date 未満 / 指定範囲内といった排他条件を用いることで将来データ参照を防止
- OpenAI 統合
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - レスポンスは JSON mode を前提としつつ、前後テキスト混入時の最外 {} 抽出による復元処理を備える
  - テスト用に _call_openai_api をパッチ差し替え可能
- フェイルセーフ設計
  - API 呼び出し失敗時は例外を投げずにフェイルセーフ値（例: macro_sentiment=0.0）を使って継続する箇所があるため、ETL やスコア計算が部分的に失敗しても他の処理は継続する
- トランザクション保護
  - market_regime / ai_scores 等の DB 書き込み時に BEGIN / DELETE / INSERT / COMMIT を行い、例外時は ROLLBACK を試行
  - ROLLBACK 失敗時は警告ログを出力して上位に例外を伝播
- DuckDB 互換性
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）問題を回避するため、空チェックを入れてから executemany を実行

### セキュリティ (Security)
- API キーと各種シークレットは環境変数から取得
- .env 自動ロード時、既存の OS 環境変数は保護され上書きされない（.env.local は上書き可能だが OS 環境変数は protected）
- 設定に未設定の必須値がある場合は明示的に ValueError を発生させる（例: OPENAI_API_KEY 未設定など）

### 既知の制限 / 将来的改善候補
- news_nlp の出力フォーマット・スキーマ検証は現状で堅牢化されているが、LLM の挙動変化に対するさらなる保険（スキーマバリデータやより厳格な応答検査）が望まれる
- 一部のネットワークエラーや API エラーはログを残してスキップする設計のため、運用時に詳細な監査・アラート機構を整備する必要がある
- 現時点では PBR・配当利回り等のバリュー指標は未実装

---

メジャーリリース以降は、このファイルに変更履歴を追記していきます。