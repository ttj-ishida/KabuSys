# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルは、提供されたコードベース（バージョン情報: 0.1.0）から実装内容を推測して作成した変更履歴です。

## Unreleased
（なし）

---

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に設定（src/kabusys/__init__.py）。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - シェル形式の export キーやクォート、インラインコメント等に対応した堅牢な .env パーサを実装。
    - OS 側の環境変数を保護する protected 機構、override フラグにより .env.local で上書き可能。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供。主要設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、Slack トークン、DB パス、環境モード、ログレベル等）をプロパティで取得。
    - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を導入。

- データ関連（Data Platform）
  - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - DB（market_calendar）優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・冪等保存を実装（取得失敗時は安全に 0 を返す）。
    - 最大探索日数や健全性チェックなど無限ループや異常データに対する防護を導入。

  - ETL / パイプライン基本機能を追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult データクラスを定義し ETL 実行の集計・監査用情報（取得件数、保存件数、品質問題、エラー一覧）を保持・辞書化できるようにした。
    - 差分取得、バックフィル、品質チェックフレームワーク（quality モジュールと連携）が想定された設計。
    - DuckDB との互換性を考慮したテーブル存在チェック・最大日付取得ユーティリティを提供。
    - data.etl で ETLResult を再エクスポート。

  - jquants_client（参照）との連携を想定した設計（calendar/pipeline が jq を利用）。

- リサーチ（Research）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum: 約1ヶ月/3ヶ月/6ヶ月 リターン計算、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、ATR割合、20日平均売買代金、出来高比率等。
    - Value: PER（EPS が 0/欠損なら None）、ROE（最新財務データから）を計算。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照する安全な実装。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（複数ホライズンの LEAD を用いた高速取得）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）。
    - ランク変換（同順位の平均ランク取り扱い）やファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージの __init__ で主要関数群と zscore_normalize をエクスポート。

- AI（自然言語処理 / レジーム検知）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに前日15:00 JST〜当日08:30 JST のニュースを対象にセンチメントを OpenAI（gpt-4o-mini）で評価。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリムするトークン肥大化対策。
    - JSON Mode を利用して厳密な JSON を期待し、レスポンスのバリデーションとスコアの ±1.0 クリップを実施。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、フェイルセーフ設計（失敗時はそのチャンクをスキップして継続）。
    - DuckDB への書き込みは対象コードに絞った DELETE → INSERT の冪等処理（部分失敗時に既存スコアを保護）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はニュース NLP のウィンドウ計算を利用（calc_news_window）。
    - OpenAI 呼び出しはリトライ・エラー処理を実装、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - DB への書き込みは BEGIN / DELETE / INSERT / COMMIT のトランザクションで冪等保証。ROLLBACK の失敗時にも警告ログを出力。

  - AI モジュールはテスト性を考慮して _call_openai_api を内部関数として分離しており、unittest.mock.patch により差し替え可能。

- 共通の運用・堅牢性
  - OpenAI 呼び出しに対して共通のエラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）を取り扱い、再試行 / フォールバックを実装。
  - 多くの処理で「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計に従う（target_date を明示的に渡す API）。
  - DuckDB のバージョン差分に配慮した実装（executemany の空リスト回避、リストバインドの互換性への注意）を導入。
  - ロギングを各モジュールに導入し、処理状況や警告を明示的に出力。

### 変更 (Changed)
- 初回リリースにつき、特段の変更履歴はなし（初版実装）。

### 修正 (Fixed)
- 初回リリースにつき、修正履歴はなし（初版実装）。

### 削除 (Removed)
- 初回リリースにつき、削除履歴はなし。

### セキュリティ (Security)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を明示的に要求する設計。キー未設定時は ValueError を送出して誤動作を防止。

---

注意事項（移行 / 利用上のポイント）
- OpenAI 利用
  - デフォルトで gpt-4o-mini を使用するように設計されています。API 利用には OPENAI_API_KEY を環境変数または関数引数で渡す必要があります。
  - API 呼び出しの結果検証（JSON パース・スキーマ確認）に失敗した場合はログ出力のうえ安全側（0.0 やスキップ）へフォールバックします。

- 環境変数
  - .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後（ルートが無い環境）では無効化される可能性があります。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB（DuckDB）書き込み
  - ai_scores / market_regime などへの書き込みは冪等性を意識した DELETE→INSERT、トランザクション制御を行っています。部分失敗時も既存データ保護を優先します。

- テスト性
  - 内部の OpenAI 呼び出しはモック差し替え可能（unittest.mock.patch を想定）で、外部 API を叩かずにユニットテストが可能です。

もし特定の変更点をより詳細に書き起こしてほしい箇所（例えば AI モジュールのエラーハンドリングの詳細、ETLResult のフィールド仕様など）があれば、その対象を指定してください。