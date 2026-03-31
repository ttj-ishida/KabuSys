# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
リリースの順序は新しいものが上です。

## [0.1.0] - 初期リリース (Unreleased)
最初の公開バージョン。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ採用、バージョン __0.1.0__ を設定。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に定義）。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機構を実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得。
    - 必須項目は取得失敗時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）やログレベル、環境種別（development / paper_trading / live）を扱うユーティリティプロパティを提供。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント分析 (news_nlp.score_news)
    - raw_news / news_symbols を元に記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価して ai_scores テーブルへ保存。
    - バッチ処理単位、トリム（記事数・文字数制限）、最大リトライ、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ等を実装。
    - レスポンス検証機構を実装し、不正レスポンスはスキップするフェイルセーフ挙動。
    - テスト用に _call_openai_api を patch 可能（ユニットテスト容易化）。
    - calc_news_window ユーティリティ（JST ウィンドウ → UTC naive datetime 変換）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定を行い market_regime へ冪等書き込み。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）、API リトライ挙動、フェイルセーフ（API 失敗時は macro_sentiment=0.0）等を実装。
    - ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を参照せず、必ず target_date 引数を使用。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (pipeline.ETLResult / data.etl 再エクスポート)
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した ETLResult データクラスを実装。
    - DuckDB を用いた最大日付取得などのユーティリティを実装。
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルの夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティを実装。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - JPX カレンダー取得用の jquants_client 経由の差分取得と冪等保存を想定。
    - 健全性チェック・バックフィル設定を含む。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）計算関数を実装。
    - DuckDB SQL を用いた実装で、prices_daily / raw_financials のみ参照。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 警告 / 注意事項 (Notes)
- 環境変数関連
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照時に必須チェック）。
  - OpenAI API は各 AI 関数で OPENAI_API_KEY（もしくは関数引数 api_key）を参照。未設定の場合は ValueError を送出。
  - .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後の安全策）。
- DB スキーマ期待値
  - 各機能は DuckDB の特定テーブルを前提としています（例: prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime）。これらのテーブルが存在しない場合、該当機能は適切に動作しないか None/空結果を返します。
- ルックアヘッド対策
  - AI / 指標計算モジュールは全て target_date 引数ベースで動作し、date.today()/datetime.today() を参照しない設計です（バックテスト等でのルックアヘッドバイアスを防止）。
- フェイルセーフ設計
  - OpenAI 呼び出し失敗時は例外を投げずにフェイルセーフ値（例えば macro_sentiment=0.0 やスキップ）で継続する箇所が多く存在します。部分的な失敗が全体を停止させない設計です。
- テスト性
  - news_nlp._call_openai_api / regime_detector._call_openai_api などはユニットテストで patch して置き換え可能に実装されています。
- OpenAI モデル
  - 現時点で gpt-4o-mini を使用するようにハードコードされています。将来的なモデル変更は該当定数を更新してください。

### 既知の制約
- DuckDB executemany に関する互換性考慮が散見される（空リストを渡さないガードなど）。
- 一部 SQL 文で日付のスキャン範囲をカレンダーバッファで確保しているため、データ量によってはクエリコストがかかる可能性があります。
- news_nlp / regime_detector ともに JSON Mode を前提にレスポンスを期待しているため、OpenAI の応答形式の変更があった場合にパースエラーが発生する可能性があります（その際はフェイルセーフでスキップされます）。

## 未定義 / 今後の改善案（例）
- API キー管理の強化（キーローテーション・秘密管理サービスとの連携）
- ai モジュールのモデル切替オプション化
- DuckDB スキーマのマイグレーションスクリプト追加
- より詳細な品質チェック / アラート機構の強化（メール／Slack 通知など）

---

参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/