# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定 / 設定管理
  - Settings クラスによる環境変数ベースの設定取得（src/kabusys/config.py）。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化。
  - .env パーサ実装（export 形式やクォート・インラインコメントの考慮）。
  - 必須環境変数チェック（_require）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値/パス:
    - KABU_API_BASE_URL = "http://localhost:18080/kabusapi"（デフォルト）
    - DUCKDB_PATH = data/kabusys.duckdb（デフォルト）
    - SQLITE_PATH = data/monitoring.db（デフォルト）
  - 環境名・ログレベルのバリデーション（KABUSYS_ENV, LOG_LEVEL）

- AI（LLM）関連
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へ送信し、ai_scores に書き込むワークフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - バッチ送信（最大 20 銘柄 / チャンク）、1銘柄当たりのトリム（最大記事数・文字数）を実装。
    - JSON Mode を期待したレスポンス検証・パース処理（レスポンスから results を抽出）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - フェイルセーフ: API エラーやパース失敗時は該当チャンクをスキップし、例外を破壊的に投げない設計。
    - DuckDB 互換性のため executemany を用いた置換（DELETE → INSERT）処理。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を取得。
    - 再試行（RateLimit/接続/タイムアウト/5xx）とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - DB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

  - AI パッケージ公開要素（src/kabusys/ai/__init__.py）:
    - score_news をエクスポート。news_nlp の機能を外部利用可能に。

- データ基盤（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - JPX カレンダー夜間更新ジョブ calendar_update_job（J-Quants から差分取得して保存、バックフィル・健全性チェックを実装）。
    - DB が空の場合は曜日ベースでのフォールバック（週末を非営業日扱い）。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数 / 保存数 / 品質問題 / エラーの集約）。
    - 差分更新、backfill、品質チェック（quality モジュールを利用）等の設計方針に準拠。
    - jquants_client 経由での Idempotent 保存を前提とする実装。
    - etl.py で ETLResult を再エクスポート。

  - 内部ユーティリティ
    - テーブル存在チェック、日付最大値取得等のユーティリティ実装。

- Research（リサーチ用分析）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を計算する関数を実装。
    - データ不足時は None を返す設計。
    - 公開 API: calc_momentum, calc_value, calc_volatility

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）ベースの IC 計算実装。
    - pandas 等に依存しない純 Python 実装。

  - research パッケージの __all__ で主要関数をエクスポート。

- その他
  - DuckDB をデータベースとして前提にした各種実装（SQL と Python のハイブリッド）。
  - ロギング出力を各モジュールで適切に実装。
  - LLM 呼び出し部分はテスト容易性のため内部呼び出し関数（_call_openai_api）を定義し、ユニットテストで差し替え可能に。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数で管理する設計。自動 .env ロードは OS 環境変数を保護する機能（protected set）を備える。

### Breaking Changes
- なし（初回リリース）

### Notes / Known behaviors
- 時刻・日付の扱い
  - AI スコア算出やレジーム判定では date.today() / datetime.today() を直接参照せず、外部から target_date を渡す方式を採用（ルックアヘッドバイアス防止）。
  - ニュースウィンドウ等は JST/UTC の変換を明示しており、DB 内は UTC 想定（naive datetime を使用）。

- フェイルセーフ設計
  - LLM 呼び出しや外部 API 呼び出しでの失敗は可能な限りフェイルセーフ（スコアに中立値を使う、チャンクスキップ、エラー集約）で処理を継続する設計。

- DuckDB 互換性
  - executemany に空リストを渡せないバージョン問題への対応がある（空チェックを実施）。

- テスト容易性
  - LLM 呼び出し箇所は内部関数をモック可能にしている（unittest.mock.patch を想定）。

----

今後のリリースでは以下を検討してください（例）:
- ai モジュールでのモデル選択や応答フォーマットの柔軟化
- jquants_client のエラーハンドリング強化とリトライ戦略の一貫化
- モニタリング / メトリクス出力の追加
- 単体テスト・統合テストの追加と CI の整備

---