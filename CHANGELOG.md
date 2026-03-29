CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。詳しくは https://semver.org/ を参照してください。

## [Unreleased]
- 今後のリリースに向けた予定事項や TODO（未定義）

## [0.1.0] - 2026-03-29
初回公開リリース。本リリースでは日本株自動売買／リサーチ基盤のコア機能群を実装しています。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージとして data, research, ai, … を想定。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等をプロパティとして安全に取得。
  - 必須環境変数未設定時は ValueError を送出する設計（例: OPENAI_API_KEY, SLACK_BOT_TOKEN）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装。
    - バッチサイズ、トリム長、リトライ（429/ネットワーク/タイムアウト/5xx 対応、指数バックオフ）を導入。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング。
    - スコア結果を ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（_call_openai_api の patch 想定）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し、スコア合成、冪等 DB 書き込みを実装。
    - API失敗時は macro_sentiment = 0.0 としてフェイルセーフ処理。
    - LLM 呼び出しは独自実装でモジュール結合を抑制（news_nlp と意図的に分離）。

- データ基盤（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休場）を採用。
    - calendar_update_job を実装し、J-Quants から差分取得して冪等的に保存（バックフィルや健全性チェック含む）。
  - pipeline / etl / ETLResult
    - ETLResult データクラスを導入（ETL 実行結果・品質問題・エラーログを集約）。
    - 差分更新・バックフィル・品質チェックを想定した ETL 設計を反映。
    - jquants_client 経由のデータ取得・保存を想定したパイプライン API（実装は jquants_client に依存）。
  - DuckDB を前提とした実装と互換性考慮（executemany の空リスト回避などの注意点）。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）などのファクターを DuckDB SQL を用いて計算。
    - データ不足時に None を返す等、健全性考慮。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）、rank、factor_summary 等の統計ユーティリティを実装。
    - 外部ライブラリに依存しない純 Python 実装（標準ライブラリ + DuckDB）。
  - zscore_normalize を data.stats から再利用可能にするエクスポート整備。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の読み込みに際し OS 環境変数を protected として .env による上書きを制御（.env.local は override=True だが保護対象キーは上書きされない）。
- OpenAI キーや Slack トークン等、機密値は環境変数から取得する設計。未設定時は明示的にエラーを出すことで運用ミスを早期検出。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI 呼び出しは gpt-4o-mini を想定。API 仕様やレスポンス形式の変更に伴う対応が必要になる可能性あり。
- 一部の DB バインド方法（DuckDB のバージョン依存）へ互換性対策を実装しているが、実運用前に使用する DuckDB バージョンでの検証を推奨。
- 日時取り扱いはすべて timezone-naive な date / datetime を使用する方針。UTC / JST の変換ロジックはモジュール内に明記されているので運用時に注意。
- 本リリースは「計算・判定・保存」ロジックに重点を置き、実際の発注（kabu 実行・strategy 実行ループ等）は別モジュール（execution, strategy 等）で実装予定／想定。

### マイグレーション / 移行手順
- なし（初回リリース）

---

貢献者: 初期実装者（自動生成ドキュメントに基づく推測）  

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして公開する際は、実装者・リリース担当者により内容確認・修正してください。