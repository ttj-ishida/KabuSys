# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-29

### 追加
- 基本パッケージ初期実装を追加
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）を追加。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などを考慮。
  - 重要環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス、環境/ログレベルの検証含む）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）を提供。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む機能を実装（score_news）。
  - タイムウィンドウ計算ユーティリティ calc_news_window（JST を基準に UTC naive datetime を返す）。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり最大記事数と文字数でのトリム、JSON Mode を用いた応答パースを実装。
  - 再試行ロジック（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）と、部分失敗時の部分書き込み戦略（書き込み前に該当コードのみ DELETE → INSERT）を実装。DuckDB 0.10 の executemany 空リスト制約に配慮。
  - レスポンス検証（JSON 抽出、results リスト検査、コード整合性、数値検証）とスコアの ±1.0 クリップ。
  - テスト容易性: OpenAI 呼び出し箇所を内部関数で分離し unittest.mock.patch による差し替えを想定。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装（score_regime）。
  - ETF の MA200 乖離計算、マクロ記事フィルタ（キーワードリスト）、OpenAI 呼び出し、レスポンスパース、合成ルール、閾値判定を実装。
  - API 呼び出し失敗時は macro_sentiment = 0.0 とするフェイルセーフ動作。
  - OpenAI 呼び出しを独立実装とし、モジュール結合を避ける設計。

- データ処理基盤（kabusys.data）
  - ETL 結果を表すデータクラス ETLResult の実装と再エクスポート（kabusys.data.pipeline.ETLResult を kabusys.data.etl で公開）。
  - ETL パイプライン基盤（kabusys.data.pipeline）:
    - 差分更新の考え方、バックフィル、品質チェックの統合を想定した設計ドキュメントとユーティリティ（テーブル最大日付取得等）を実装。
    - ETLResult に品質問題やエラーの収集・辞書化メソッドを提供。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB データ優先・未登録日は曜日フォールバックの一貫した扱い。
    - calendar_update_job により J-Quants からの差分取得→冪等保存の夜間バッチロジック（バックフィル、健全性チェック）を実装。
    - テーブル未取得時の安全なフォールバック（週末除外）を実装。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL と窓関数を活用し、prices_daily / raw_financials のみ参照する設計。
    - データ不足時の None 扱いと結果を (date, code) をキーとする dict のリストで返すインターフェース。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで動作する実装。

### 変更
- 設計上の重要な方針をコード内ドキュメントとして明記
  - 全ての AI / ニュース / レジーム / リサーチ処理で datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは再試行設計とフェイルセーフ（中立スコアで継続）を採用。
  - DuckDB に対する互換性留意（executemany の空リスト問題、日付値の変換等）。

### 修正
- エラーハンドリングとログ出力を強化
  - API 呼び出し、DB 書き込み、.env 読み込み等で失敗した際に警告/例外処理を細かく実装し、ROLLBACK や警告ログを出すようにした。
  - JSON パース失敗時に最外の JSON オブジェクトを抽出する復元ロジック等、実運用でのノイズに耐える実装を追加。

### 注意事項 / 移行メモ
- OpenAI API キーは score_news / score_regime に api_key 引数として注入可能。引数省略時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出するため、運用環境では必ず設定してください。
- .env の自動ロードはプロジェクトルート (.git または pyproject.toml を基準) が見つかった場合にのみ行われます。CI/テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への書き込みは部分失敗対応（影響のあるコードのみ削除して挿入）を行うため、部分的な API 失敗時にも既存スコアを可能な限り保持します。
- 現時点では致命的な互換性破壊（Breaking Changes）はありません（初期リリース）。

---

今後のリリースでは、テストカバレッジの追加、Add-on の外部インテグレーション、パフォーマンス改善、より詳細な品質チェックのルール追加などを予定しています。