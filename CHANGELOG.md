# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装・公開。

### 追加された機能
- パッケージ初期構成
  - パッケージメタ情報と公開APIを定義（kabusys.__init__）。
  - バージョン: 0.1.0

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - OS 環境変数のキーは保護（上書き防止）される挙動を追加
  - 高度な .env パース実装: export 形式、クォート文字のエスケープ、インラインコメント処理に対応
  - Settings クラスを提供（環境変数のアクセス・バリデーションを集約）
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティとして取得
    - 無効な環境値（LOG_LEVEL, KABUSYS_ENV 等）に対する検証と明確なエラーメッセージ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini／JSON Mode）でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装
  - 主な設計・実装点:
    - スコアリング対象ウィンドウ（JST基準）：前日 15:00 〜 当日 08:30 を UTC に変換して比較
    - 銘柄ごとに最新 N 件・最大文字数でトリム（トークン肥大対策）
    - バッチ処理（デフォルト 20 銘柄/チャンク）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ
    - レスポンス検証と堅牢な JSON パース（余分な前後テキストの抽出ロジックを含む）
    - スコアを ±1.0 にクリップ
    - 部分失敗に備え、ai_scores への書き込みは対象コードのみを DELETE → INSERT（冪等性・既存データ保護）
    - テスト容易性: OpenAI 呼び出し部分は差し替えられる（ユニットテスト用のパッチポイントを用意）
  - 公開API: score_news(conn, target_date, api_key=None) → 書込み銘柄数を返す

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei-225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で書き込み
  - 主な設計・実装点:
    - ルックアヘッドバイアス回避: target_date 未満のデータのみを使用、datetime.today()/date.today() を参照しない
    - ma200_ratio 計算（データ不足時は中立値 1.0 を返す + 警告ログ）
    - マクロキーワードリストに基づく raw_news タイトル抽出（最大 20 件）
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）とリトライ処理、失敗時には macro_sentiment=0.0 でフェイルセーフ
    - 合成スコアのクリップと閾値に基づくラベル付け（bull/neutral/bear）
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
  - 公開API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す

- データプラットフォーム（kabusys.data）
  - ETL パイプライン:
    - ETLResult データクラス（取得数・保存数・品質チェック結果・エラー等を収集）
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールを利用）
  - カレンダー管理（market_calendar）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装
    - DB にカレンダーがない場合は曜日ベースでフォールバック（土日休）
    - calendar_update_job による J-Quants からの差分フェッチと保存（バックフィル・健全性チェックを含む）
    - 最大探索範囲やバックフィル日数等の設定により安全性を確保
  - jquants_client 経由の差分取得・保存を想定（関数呼び出しポイントを使用）

- リサーチ（kabusys.research）
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足で None を返す）
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials から最新の報告を用いる）
  - 特徴量探索・統計:
    - calc_forward_returns: 将来リターン（任意ホライズン。デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算（不足データ/小サンプルは None）
    - rank: 平均ランク処理（同順位は平均ランク）
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）
  - 依存を最小化（pandas 等不使用）し、DuckDB を用いた SQL と純 Python の組合せで実装
  - kabusys.data.stats.zscore_normalize を再エクスポートして利用可能に

### 改善点（設計上の考慮）
- すべての時刻・日付処理でルックアヘッドバイアスを避ける設計を採用（target_date を明示的に受け取る）
- 外部 API 呼び出しに対する堅牢なエラーハンドリングと再試行ロジックを導入（OpenAI, J-Quants など）
- DuckDB との互換性を考慮した実装（executemany の空リスト回避、日付変換ユーティリティ等）
- テスト容易性を考慮したフック（OpenAI 呼び出しの差し替えポイント等）

### 修正・不具合対応
- （初期リリースのため過去の修正履歴なし。ただし各モジュールに例外発生時のログ・ロールバック処理を実装）

### 既知の注意点（ドキュメント的な注意）
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を発生させる（引数での注入または環境変数 OPENAI_API_KEY を設定する必要あり）
- .env の自動読み込みを行うが、テストや特殊用途で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- 一部機能は外部クライアント（jquants_client、kabu ステーションクライアント等）に依存し、これらのクライアント実装は別モジュールを想定

### セキュリティ
- API キーやパスワードは Settings を通じて環境変数から取得。未設定時は明確な例外メッセージで失敗させる設計。

## 破壊的変更
- なし（初期リリース）

---

今後のリリースでは以下を予定（例）
- 監視（monitoring）モジュールの実装とドキュメント化
- jquants_client の具体的実装と ETL pipeline の統合テスト
- 追加の品質チェックルールおよびアラート連携（Slack 通知等）
- パフォーマンス最適化と大規模データに対するベンチマーク結果の反映

もし特定の変更やリリース日付の調整、より詳細なチケット／コミットベースの履歴分割を希望される場合は、その情報を提示してください。