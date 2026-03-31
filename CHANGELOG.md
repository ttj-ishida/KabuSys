# CHANGELOG

すべての重要な変更点を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠した形式で日本語で記載します。

注意: バージョン番号はパッケージ内の __version__（0.1.0）に基づく初期リリースの想定記述です。コード内容から実装された機能・設計判断を推測して記載しています。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-31
初期公開リリース — 日本株自動売買システム「KabuSys」の基本モジュール群を追加。

### 追加 (Added)
- パッケージ公開の基本構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージAPIの外形を定義）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に検出）
  - export KEY=val 形式やクォート・エスケープ、行コメントのパーシングに対応
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack、DB パス、監視閾値、環境・ログレベル判定等）
  - 必須環境変数未設定時に明示的な例外を投げる _require() 実装

- AI 関連モジュール (src/kabusys/ai/)
  - ニュースセンチメントスコアリング: news_nlp.score_news
    - raw_news / news_symbols から銘柄ごとに記事を集約し OpenAI (gpt-4o-mini) の JSON mode で一括スコア取得
    - バッチサイズ / トリム文字数 / リトライ（429・ネットワーク断・タイムアウト・5xx）を実装
    - レスポンスのバリデーション（results 配列、code と score、数値チェック）と ±1.0 へのクリップ
    - DuckDB 互換性を考慮した部分置換（DELETE → INSERT）で冪等性確保
    - テスト容易性のため _call_openai_api を patch 可能に実装
  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）
    - prices_daily / raw_news / market_regime テーブル参照、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出しは独立実装（news_nlp と private 関数を共有しない）
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 にフォールバック
    - 再試行・エクスポネンシャルバックオフ実装

- データ関連モジュール (src/kabusys/data/)
  - カレンダー管理: calendar_management
    - market_calendar テーブルベースの営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 未取得時は曜日ベース（週末除外）のフォールバックを一貫して使用
    - JPX カレンダー差分取得バッチ（calendar_update_job）を実装し、J-Quants クライアント経由で取得・保存
    - バックフィル・健全性チェック（最大探索日数など）を実装
  - ETL パイプライン: pipeline.ETLResult / pipeline の骨組み
    - ETL 実行結果を表す dataclass (ETLResult) を実装（取得数・保存数・品質問題・エラーの集約）
    - DataPlatform 設計に基づく差分取得・品質チェックの指針を実装方針コメントとして追加
  - etl モジュールで pipeline.ETLResult を公開再エクスポート

- リサーチ・ファクター群 (src/kabusys/research/)
  - factor_research: calc_momentum / calc_volatility / calc_value
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR20、平均売買代金、出来高比率、PER/ROE を DuckDB SQL で計算
    - データ不足時の扱い（None）やスキャン範囲バッファを実装
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
    - 将来リターン計算（任意ホライズン、入力検証）、IC（Spearman ランク相関）計算、統計サマリー、ランク関数を実装
  - 研究用ユーティリティをまとめて __all__ で公開

### 変更 (Changed)
- （初回リリースのため「変更」はなし。将来のリリースで履歴を追加予定）

### 修正 (Fixed)
- （初回リリースのため「修正」はなし）

### セキュリティおよび設計上の注意点 (Notes)
- 環境変数の自動読み込みは、既存の OS 環境変数を protected として上書きしない挙動（.env.local は override 可）を採用
- OpenAI API キーや Slack トークン等は環境変数で扱い、未設定時は明示的にエラーを返す設計
- API 呼び出し部分にはリトライとフォールバックを実装しており、外部依存の失敗で全体が停止しないように配慮
- ルックアヘッドバイアス防止: 各モジュールで date.today()/datetime.today() に依存せず、target_date を明示的に受け取る実装方針を採用
- DuckDB のバージョン差異（executemany の空リスト問題、リスト型バインドの不安定性）を考慮した実装がなされている

### 既知の制約・将来対応候補 (Known limitations / Future work)
- strategy / execution / monitoring 等のエントリポイントはパッケージ公開の外形を定義済みだが、実稼働向けの発注ロジックやモニタリング連携は別途実装が必要
- 一部の J-Quants クライアントや外部依存（jquants_client）の実装は別モジュールとして参照されており、CI/実行環境での設定が必要
- OpenAI のレスポンス形式の変化に備えてバリデーションは堅牢化しているが、将来的な API 変化に対する追加対応（モデル切替やレスポンス仕様差異の吸収）は継続検討

---

作成者注:
- 本 CHANGELOG は提示されたソースコードの内容およびコメント（設計方針）から推測して作成しています。実際のリリース履歴や日付はプロジェクト運用に合わせて編集してください。