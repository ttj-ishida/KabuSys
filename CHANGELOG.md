# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  
https://keepachangelog.com/ja/1.0.0/

なお、以下の履歴は提供されたソースコードから推測して作成しています。

## [Unreleased]

- 今後の予定 / 既知の改善点（コード中の TODO 相当）
  - テストカバレッジ強化（OpenAI 呼び出しのモック化は既に意識されているが、追加のユニット/統合テストが望まれる）
  - API クライアントの抽象化や接続設定のさらなる柔軟化
  - monitoring / execution / strategy パッケージの具体的実装とドキュメント整備

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買支援のためのデータ処理・研究・AI連携基盤を提供する初期実装を追加。

### 追加
- パッケージ構成
  - kabusys パッケージの基幹モジュール群を追加（data, research, ai, config などのサブパッケージを公開）。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化対応。
  - .env パーサー実装: export 句、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いを考慮。
  - 環境変数保護（既存 OS 環境変数を protected として上書き抑制）に対応。
  - Settings クラスを追加し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env, log_level, is_live, is_paper, is_dev
  - env / log_level のバリデーション（許容値チェック）を実装。

- データ（kabusys.data）
  - calendar_management
    - JPX 市場カレンダーの管理ロジックを追加（market_calendar テーブル利用）。
    - 営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダー未取得時は曜日ベースでフォールバックする堅牢な設計。
    - calendar_update_job: J-Quants API からの差分取得と冪等保存（fetch/save のエラー処理とバックフィルを含む）。
  - pipeline / etl
    - ETLResult dataclass を公開（ETL 実行結果の集約用）。
    - ETL パイプラインの基本実装（差分取得、保存、品質チェックの統合方針とユーティリティ関数）。
    - テーブル存在チェックや最大日付取得などの補助関数実装。
  - etl モジュールで ETLResult を再エクスポート。

- 研究/特徴量（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等の計算関数を追加:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB 上で SQL を用いて効率的に計算。データ不足時の None 戻し方針を明確化。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズンバリデーションあり）。
    - IC（Spearman）計算 calc_ic（ランク付き相関、データ不足時は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）、統計サマリー factor_summary。
  - zscore_normalize を data.stats から再エクスポートする仕組み。

- AI（kabusys.ai）
  - news_nlp（ニュースセンチメント解析）
    - raw_news + news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信してセンチメントスコアを算出。
    - バッチ処理（最大20銘柄 / API 呼び出しチャンク）、1 銘柄当たりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON mode を利用して厳密な JSON 出力を期待。レスポンスのバリデーションとスコアのクリップ（±1.0）。
    - リトライ戦略（429 / ネットワーク / タイムアウト / 5xx は指数バックオフでリトライ）。非再試行のケースはスキップして継続するフェイルセーフ設計。
    - 書き込み: ai_scores テーブルへ冪等的に DELETE → INSERT（部分失敗時に他コードを保護）。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - regime_detector（市場レジーム判定）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して regime score/label を生成（bull/neutral/bear）。
    - マクロセンチメントは news_nlp の calc_news_window を利用して取得したタイトルを OpenAI に送信して算出。
    - API 呼び出しのリトライとフォールバック（API 失敗時は macro_sentiment=0.0）、スコアのクリップ、最終的な market_regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは独立実装（モジュール間でプライベート関数を共有しない設計）。
  - ai パッケージで score_news, score_regime を公開。

### 変更
- 設計上の注意点・方針を明文化
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない（target_date ベースでの計算）。
  - DuckDB を一次データバックエンドとして前提。
  - 外部 API に対してはフェイルセーフ（API 失敗で全体停止させない）設計。

### 修正（実装上の堅牢化）
- OpenAI 呼び出し周り
  - JSON パースの堅牢化（JSON mode でも余計な前後テキストが混ざるケースを考慮して {} を抽出してパース）。
  - APIError の status_code の有無に依存しない安全な扱い。
  - リトライ時の待機時間は指数バックオフで増加。
- DuckDB 書き込みの堅牢化
  - executemany に空リストを渡さないガード（DuckDB 一部バージョンの制約に対応）。
  - トランザクション周りの例外処理（ROLLBACK の失敗も警告ログに記録して上位に再送出）。

### セキュリティ
- 機密情報（API キー等）取得については明確に環境変数に依存し、未設定時は ValueError を送出して安全性を保証（OpenAI API キー、Slack トークン、Kabu API パスワード等）。

### 既知の制約/注意点
- OpenAI の API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- 一部モジュール（monitoring / execution / strategy）は __all__ に含まれているが、今回のコードベースでは詳細実装が含まれていない（将来的な追加を想定）。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）に依存する。スキーマ整合性が前提。
- 外部 API（J-Quants、OpenAI）への依存があるため、実行環境での適切な認証情報とネットワークアクセスが必要。

---

（注）日付とバージョンはソースコードから推測して付与しています。必要に応じてリリース日やバージョンを調整してください。