# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に準拠します。バージョン番号は semantic versioning に従います。

※ 内容はコードベースから推測して作成しています。

## [Unreleased]
- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能・実装を含みます。

### 追加
- 包括的な日本株自動売買フレームワーク「KabuSys」を公開
  - パッケージエントリポイント: kabusys（__version__ = 0.1.0）
  - 公開サブパッケージ（__all__）：data, strategy, execution, monitoring（外部からの利用を想定）

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - .env ファイルの柔軟なパース対応
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行内コメントの扱い（クォートの有無に応じた適切な切り取り）
    - 読み込み失敗時は警告を出力
  - .env と .env.local の優先度制御（.env.local が上書き）
  - OS 環境変数は保護され、上書きを禁止する仕組みを提供
  - Settings クラスを提供し、J-Quants、kabuステーション、LINE、DBパス、監視閾値、実行環境（development/paper_trading/live）などを環境変数から取得・検証

- データ管理（kabusys.data）
  - calendar_management:
    - JPX 市場カレンダー管理（market_calendar テーブルを使用）
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にデータがない場合は曜日（平日）ベースでフォールバック
    - 夜間バッチジョブ calendar_update_job により J-Quants から差分取得・保存（バックフィル／健全性チェックを含む）
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の構造化）
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した ETL 設計
    - jquants_client と連携して安全にデータ保存（冪等性を意識）
  - etl モジュールは ETLResult を再エクスポート

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価
  - タイムウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC に換算して DB を検索）
  - 銘柄あたりの最大記事数・最大文字数でトリム（トークン肥大化対策）
  - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE）
  - API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ）
  - JSON mode のレスポンスを厳密にバリデーションし、必要に応じて余分な前後テキストから JSON 部分を抽出して復元
  - スコアは ±1.0 にクリップして ai_scores テーブルへ安全に置換（DELETE → INSERT、部分失敗時に他コードを保護）
  - API キー注入（引数または OPENAI_API_KEY 環境変数）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
  - LLM（gpt-4o-mini）を用いたマクロセンチメント評価
  - レジームスコア計算式、閾値（BULL/BEAR）、クリッピング、ラベル決定を実装
  - API 呼び出しのリトライ、API 失敗時は macro_sentiment を 0.0 とするフェイルセーフ
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比を計算
    - calc_value: raw_financials から最新財務を取得し PER・ROE を計算
    - 設計上、DuckDB 接続を受け取り SQL で処理し、外部 API へ依存しない
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（結合・フィルタリング・同順位平均ランク対応）
    - rank: 同順位は平均ランクを与える安定実装（丸めで ties 検出の安定化）
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）
    - 外部ライブラリに依存せず標準ライブラリのみで実装

- 基盤的実装・小改善
  - DuckDB を主要なデータストアに採用し、各モジュールで DuckDB 接続を受け渡す設計
  - ロギング（logger）を各モジュールに配置し情報・警告・例外時のログ出力を充実
  - API エラー種別（RateLimitError, APIConnectionError, APITimeoutError, APIError）を考慮した堅牢なエラーハンドリング

### 変更
- （初回リリースのため該当なし）

### 修正
- ニュース NLP と レジーム判定で JSON レスポンスのパース失敗や API エラー時にフェイルセーフ（スコアを 0.0 にフォールバック）を明示的に実装
- DuckDB の executemany に対する互換性問題に対応（空リストを渡さないガードを追加）
- market_calendar が未登録のときに曜日ベースで一貫してフォールバックする挙動を明文化

### 既知の制約 / 注意事項
- OpenAI（gpt-4o-mini）や J-Quants、kabuステーション 等の外部 API キー/接続が必要な機能がある（環境変数を参照）
- time.now()/date.today() をコード内で直接参照しない設計で、ルックアヘッドバイアス対策を実装しているが、ETL 実行者は target_date を明示的に渡すことが推奨される
- 一部テーブル（market_calendar, prices_daily, raw_news, ai_scores, market_regime 等）のスキーマが前提となるため、実行前に DB スキーマを整備する必要あり

---

参考: この CHANGELOG はソースコードのコメント・実装に基づく推測記述です。実際のリリースノートとして使用する際は、テスト結果やリリースポリシーに従って内容を調整してください。