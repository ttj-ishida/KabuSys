# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
日付は本リリースの想定日です（コード内容から推測して作成）。

## [Unreleased]
- （現時点の差分はありません）

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点・設計方針・注意点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ による公開）。

- 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 強化された .env パーサ:
    - export KEY=val 形式対応、シングル/ダブルクォート＋バックスラッシュエスケープ対応。
    - インラインコメント処理（クォート有無での取り扱い差分を考慮）。
  - 環境変数取得ユーティリティ Settings を提供。必須項目は取得時に ValueError を投げる:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
  - 各種設定プロパティ（DB パス、閾値、環境判定、ログレベル等）。

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数・文字数トリミング、JSON Mode レスポンス検証、±1.0 でクリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット、未知コードの無視等）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api がパッチ可能）。
    - calc_news_window: JST基準のニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算。

  - kabusys.ai.regime_detector
    - ETF(1321) の 200 日移動平均乖離（70% 重み）とニュース由来の LLM センチメント（30% 重み）を合成して市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満のみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードベース（複数キーワード定義）で最大記事数制限。
    - OpenAI 呼び出しのリトライ、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - OpenAI クライアントは引数経由または環境変数 OPENAI_API_KEY から解決。

- データモジュール
  - kabusys.data.calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）と営業日判定ユーティリティを実装。
    - market_calendar テーブルがない場合は曜日（土日）ベースでフォールバック。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。探索上限により無限ループを防止。
    - J-Quants クライアント経由の差分取得・バックフィル・健全性チェックを実装。

  - kabusys.data.pipeline, kabusys.data.etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題やエラー情報の保持）。
    - ETL パイプライン方針: 差分更新、idempotent な保存（ON CONFLICT / delete+insert の慎重な扱い）、品質チェックは全件収集型で Fail-Fast としない設計。

- 研究 (research) モジュール
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、流動性指標、財務指標（PER, ROE）等のファクター計算関数を実装。
    - DuckDB SQL を多用して効率的に集計（窓関数、LAG/LEAD、平均等）。
    - データ不足時の扱い（必要行数未満で None を返すなど）。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）による IC 計算、同順位は平均ランク処理。

### 変更 (Changed)
- 初回リリースのため過去の変更はありません（0.1.0 としての追加のみ）。

### 修正 (Fixed)
- 初回リリースのため過去の修正履歴はありません。
- 実装面で明示的に耐障害性（API リトライ、レスポンスパース失敗時のフォールバック、DB トランザクションのロールバック処理など）を強化。

### 注意点 / 既知の仕様（重要）
- OpenAI API キーは api_key 引数経由または環境変数 OPENAI_API_KEY で指定する必要があります。未設定時は ValueError が発生します。
- .env の自動読み込みはプロジェクトルートを基に行うため、配布後やテストで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany に空リストを渡せないバージョンへの互換性考慮（空チェックを実装）。
- ルックアヘッドバイアス対策: 日付ベースの処理は内部で date.today()/datetime.today() を直接参照せず、必ず target_date を受け取る形で実装。
- market_calendar が不完全な場合は DB の値を優先しつつ、未登録日は曜日ベースのフォールバックで一貫した振る舞いを保証。
- LLM 出力は厳密な JSON を期待する設計だが、まれに前後に余計なテキストが混入するケースがあるため復元処理やバリデーションで堅牢化している。
- ai_scores / market_regime など DB 書き込みは冪等性を意識した DELETE→INSERT または ON CONFLICT 相当の処理を行う。

### セキュリティ (Security)
- API キーやシークレットは環境変数経由で扱うことを想定。.env ファイルを使用する場合はローカルに留め、公開リポジトリに含めないでください。
- 自動 .env 読込はデフォルトで有効だが、CI/テスト環境などでは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### テスト性 / 拡張性
- OpenAI 呼び出し箇所（_call_openai_api）はユニットテストで差し替え（patch）可能に設計。
- DuckDB 接続を受け取る設計により、外部サービスに依存しない単体テストが容易。
- 各モジュールは副作用を限定（DB 書き込みは明示的な関数で実行）してあり、研究用途と本番発注ロジックの分離が図られている。

---

補足:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。内部で参照している外部モジュール（jquants_client など）や未表示のファイルがあるため、実際のリリースノートでは外部 API のバージョン情報、依存関係、マイグレーション手順等を追記してください。