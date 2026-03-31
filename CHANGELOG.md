# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
バージョン番号はパッケージ内の __version__ を基にしています。

※ 内容は与えられたコードベースから推測して作成しています。実際の変更履歴やコミットメッセージとは異なる可能性があります。

## [0.1.0] - 2026-03-31

### 追加
- 初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py にてパッケージ名と __version__ = "0.1.0" を設定。トップレベルの公開モジュールは data, strategy, execution, monitoring。
- 環境設定管理
  - src/kabusys/config.py を追加。
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 複雑な .env のパース処理に対応（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理など）。
    - Settings クラスを公開（J-Quants / kabu API / Slack / データベースパス / 監視閾値 / 環境判定ロジック 等）。
    - 必須環境変数が未設定の場合は ValueError を送出する _require() を実装。
    - 有効な環境名・ログレベルの検証を実装。
- AI（NLP）機能
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたり記事トリム（記事数・文字数制限）によるトークン肥大対策を実装。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライを実装。
    - レスポンスの厳密なバリデーション、JSON 前後ノイズ復元ロジック、スコアのクリップを実装。
    - DB 書き込みは冪等化（DELETE→INSERT、部分失敗時に既存スコアを保護）している。
    - calc_news_window 関数により JST の前日15:00〜当日08:30 のウィンドウを UTC naive datetime で計算するユーティリティを提供。
  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワードリスト、最大記事数、OpenAI 呼び出しのリトライ / フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - API 呼び出しは gpt-4o-mini を使用し JSON を期待。レスポンスパース失敗や API エラー時はログを残して安全にフォールバックする設計。
- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar を使った日本取引所カレンダー管理機能（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）を実装。
    - DB のカレンダーデータがない場合は曜日ベース（土日を休日）でフォールバックする一貫したロジックを提供。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィルと健全性チェック含む）。
  - src/kabusys/data/pipeline.py を追加。
    - ETL の結果を表す ETLResult データクラスを含む ETL パイプラインの基礎を実装（差分取得、保存、品質チェックのフック設計）。
    - DuckDB を前提としたテーブル有無チェックや最大日付取得ユーティリティ等を含む。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - jquants_client や quality などの外部 Client 連携ポイントを想定した構成（実装は参照先に依存）。
- リサーチ / ファクター
  - src/kabusys/research/factor_research.py を追加。
    - Momentum / Volatility / Value（PER, ROE）等の定量ファクター計算関数（calc_momentum, calc_volatility, calc_value）を提供。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグ・移動平均・ATR・出来高等を算出。
    - データ不足時の None 戻しやログ出力など堅牢な設計を採用。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman ランク相関）、ランク化ユーティリティ、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する方針。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- その他
  - OpenAI SDK（OpenAI クライアント）を利用する部分は client.chat.completions.create を呼ぶラッパー関数を定義。ユニットテスト時に差し替え可能な設計。
  - DuckDB を主要なローカルデータストアとして使用する設計が各モジュールに一貫している。
  - 多くの箇所で「ルックアヘッドバイアス防止」のため datetime.today() / date.today() を直接参照しない設計思想を採用（target_date を明示渡し）。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 既知の仕様・注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要があり、未指定時は ValueError を送出する。
- news_nlp/regime_detector は gpt-4o-mini の JSON Mode を前提としたレスポンスパースに依存するため、API の応答形式変更に影響を受ける可能性がある。
- .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布環境では意図せず自動ロードされない場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD や明示的な環境変数設定での運用を推奨。
- DuckDB の executemany に空リストを与えるとエラーとなるバージョン互換性に配慮した実装（空チェックを行ってから executemany を呼ぶ）。
- 市場カレンダーやデータの欠落・部分的取得に対してはフォールバックや部分書き換えなどで既存データを守る設計になっているが、完全な整合性は運用ポリシーに依存する。
- セキュリティ: 環境変数の上書きロジックでは OS 環境変数を protected として .env による上書きを防ぐ機構がある。

### セキュリティ修正
- （初期リリースのため該当なし）

---

今後の改善候補（コードから推測）
- OpenAI 呼び出し部分の抽象化・テスト用モックの追加ドキュメント化。
- J-Quants / kabu クライアント実装の標準化とエラーハンドリング強化。
- news_nlp の出力検証ルールの拡張（スキーマ検証ライブラリ導入など）。
- パフォーマンス監視・メトリクス収集の統合（ETL/AI処理時間や API レート等）。

もし特定のモジュールごとにより詳細なリリースノート（関数一覧、入出力仕様、例など）が必要であれば、対象モジュールを指定していただければ個別に展開します。