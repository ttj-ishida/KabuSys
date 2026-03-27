# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

現在のバージョン: 0.1.0

## [Unreleased]
（無し）

---

## [0.1.0] - 2026-03-27
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - パブリックモジュール群をエクスポート: data, strategy, execution, monitoring。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートの探索は __file__ を基点に `.git` または `pyproject.toml` を探索し、CWD に依存しない実装。
  - .env パーサを実装（コメント行、export プレフィックス、シングル／ダブルクォート、エスケープ対応、インラインコメント判断など）。
  - 環境変数の保護機能（既存 OS 環境変数は .env による上書きを防ぐ protected ロジック）。
  - Settings クラスを提供し、必須設定の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）とバリデーションを行う。
  - DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）および環境に基づく挙動（env, log_level, is_live 等）。

- データ関連 (src/kabusys/data/)
  - カレンダー管理モジュール (calendar_management.py)
    - JPX カレンダー管理・夜間更新ジョブ（calendar_update_job）を実装。
    - 営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar テーブルが未取得の場合は曜日ベース（土日休）でフォールバックする堅牢設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）・バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py 経由で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を行う設計。
    - DuckDB との互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを実装。
    - ETL の結果や品質問題を収集する構造を提供。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum: 約1/3/6ヶ月リターン（営業日ベース）と 200 日移動平均乖離（ma200_dev）。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER, ROE（raw_financials から最新財務データを取得して算出）。
    - DuckDB を用いた SQL ベースの処理。データ不足時は None を返す堅牢な実装。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランクで処理）。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を持たない純標準ライブラリ + DuckDB 実装。

- AI（自然言語処理 / LLM）モジュール (src/kabusys/ai/)
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）に送信し、センチメント（ai_scores）を算出・書き込み。
    - 時間ウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実行）を対象にする calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり最大記事数・最大文字数でトリムしてトークン膨張を抑制。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライ。非リトライ系エラーはスキップして継続するフェイルセーフ設計。
    - レスポンスの厳密なバリデーション（JSON 抽出、results フォーマット確認、既知コードのみ採用、数値バリデーション、±1.0 クリップ）。
    - 書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT の冪等的処理。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch 推奨）。
    - パブリック API: score_news(conn, target_date, api_key=None) を提供。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースの抽出はキーワードベース（複数キーワードを含む検索）で最大 20 件を渡す。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント算出、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - スコア合成後、market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT を用いた冪等書き込みを行う。
    - ルックアヘッドバイアス防止の設計（datetime.today() を参照しない、prices_daily の date < target_date を厳守）。
    - パブリック API: score_regime(conn, target_date, api_key=None) を提供。

- 低レベル実装・運用上の配慮
  - DuckDB を主要な分析 DB として利用。クエリや書き込みは互換性・安全性を考慮して実装。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性と整合性を確保。ROLLBACK 失敗時は警告ログ出力。
  - 外部 API 依存（OpenAI、J-Quants）の失敗に対するフォールバックやログ出力を徹底（フェイルセーフ設計）。
  - テストの容易性を意識したフック（_call_openai_api の差し替え等）を用意。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- 該当なし。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成した初期の変更履歴です。実際のコミット履歴やリリースノートと異なる場合があります。必要に応じて日付・内容の調整を行ってください。