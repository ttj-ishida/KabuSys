# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下は主要な追加点・設計上の特徴・挙動の要約です。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報とエクスポート: kabusys.__version__ = 0.1.0、主要サブパッケージ（data, research, ai 等）を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数読み込み機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、行末コメントルールに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 環境種別・ログレベルなどを取得。未設定値の検出時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の明示的チェック）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - Raw ニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメントスコア（-1.0〜1.0）を算出。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）と、それに基づく calc_news_window 実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。API 失敗時はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（取得したコードのみ DELETE → INSERT）で部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し箇所の差し替えポイントを用意（内部関数の patch 想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、JSON 解析、リトライ・フォールバック（API 失敗時に macro_sentiment = 0.0）。
    - レジームスコア合成ロジック、閾値によるラベリング、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計（外部から target_date を注入）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日扱い）。
    - 最大探索日数制限や健全性チェック（過度に未来の日付を検出した場合のスキップ）を実装。
    - J-Quants クライアントとの連携ポイント（fetch/save）を利用。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得数・保存数・品質問題一覧・エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェックの設計に沿ったユーティリティ群を実装。
    - DuckDB 上でのテーブル存在チェック、最大日付取得などのヘルパーを実装。
    - DuckDB の executemany が空リストを受け付けない制約を考慮した実装（保存前に空チェック）。

- リサーチ/因子計算 (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL / Python で計算する関数（calc_momentum, calc_volatility, calc_value）。
    - データ不足時に None を返すなど堅牢な挙動。
  - feature_exploration モジュール
    - 将来リターンの計算（calc_forward_returns）：複数ホライズンに対応、引数検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関（ランクは同順位を平均ランクで処理）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリ（factor_summary）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの扱いは引数注入または環境変数（OPENAI_API_KEY）を明示的に要求し、未設定時には ValueError を投げることで不正な実行を防止。

### 設計上の注意点 / 既知の挙動
- ルックアヘッド回避: 多くのモジュール（news_nlp, regime_detector, research 等）は内部で date.today() や datetime.today() を参照せず、外部から target_date を渡す設計。バックテストや信頼性の高い過去評価に対応。
- フェイルセーフ: OpenAI 呼び出しや外部 API の失敗時にはスキップ（macro_sentiment = 0 または該当銘柄のスコアを取得できなかった場合は未保存）して処理継続する設計。
- DuckDB 互換性: executemany の仕様差分（空リスト不可等）に配慮した実装を行っているため、古い DuckDB バージョンでも安定動作を目指す。
- テストのしやすさ: OpenAI 呼び出し部分は内部関数を patch して差し替えることを想定している（ユニットテストでのモック容易化）。

---

（今後のリリースでは、発注/実行 (execution)、監視 (monitoring) 関連の実装、さらに詳細な品質チェック・メトリクスの強化、性能向上や追加指標の実装を予定しています。）