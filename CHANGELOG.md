# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
このファイルは後続のリリースでも継続的に更新してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-31
初回リリース（ベース実装）。主要なコンポーネントを実装しました。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン __version__ = "0.1.0"、公開モジュール一覧を定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動読み込みを実現。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱い）。
  - 自動ロードの無効化オプション KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、アプリケーションで使用する主要な設定値（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル）をプロパティとして提供。必須変数未設定時は ValueError を送出。
  - env / log_level に対する検証（許容値を限定）。

- データパイプライン・ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装（ETL の集計結果、品質問題、エラー情報を保持）。
  - ETL パイプライン方針・ユーティリティを実装。DuckDB を想定した差分取得、バックフィル、品質チェックの設計が反映。

- カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダー管理機能を実装。
  - 営業日判定 API：is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
  - 夜間バッチ更新ジョブ calendar_update_job（J-Quants から差分取得して market_calendar テーブルへ冪等保存）。
  - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェック等の安全策を実装。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出して ai_scores テーブルへ保存する score_news 関数を実装。
  - 処理特徴：
    - タイムウィンドウ計算（JST → UTC 変換）、記事トリム（件数・文字数制限）、
    - 最大バッチサイズ、チャンク単位での API 呼び出し、
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ、
    - レスポンスバリデーション（JSON 抽出、results フォーマット検証、未知コード無視、数値チェック）、
    - スコアを ±1.0 にクリップして保存、
    - DuckDB の executemany の制約を考慮した安全な DELETE→INSERT の実装、
    - API 呼び出し部はモジュール内で _call_openai_api として分離し、テスト時に差し替え可能。
  - calc_news_window ユーティリティを提供（前日 15:00 JST 〜 当日 08:30 JST の記事ウィンドウ）。

- AI 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする score_regime を実装。
  - 特徴：
    - duckdb クエリで過去データのみ使用しルックアヘッドを回避、
    - マクロニュース抽出（キーワードベース）→ OpenAI で JSON レスポンスを要求、
    - API 障害時は macro_sentiment = 0.0 とするフェイルセーフ、
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx）、レスポンスパース失敗時のフォールバック、
    - OpenAI 呼び出しをモジュール内 _call_openai_api として分離しテスト容易性を確保。

- リサーチ・ファクター計算 (src/kabusys/research/*)
  - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials からファクター算出）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から取得）
  - feature_exploration モジュールを実装:
    - calc_forward_returns（任意ホライズンの将来リターンをまとめて取得。ホライズン検証あり）、
    - calc_ic（Spearman ランク相関で IC を計算、十分なサンプルが無い場合は None）、
    - rank（同順位は平均ランクで返す）、
    - factor_summary（count/mean/std/min/max/median を計算する統計サマリ）。
  - research パッケージの __init__ で主要関数を公開し、data.stats.zscore_normalize を再利用。

- データクライアント / ETL 再エクスポート (src/kabusys/data/etl.py)
  - pipeline.ETLResult を外部公開するエントリポイントを追加。

### 変更 (Changed)
- 日付・時刻の取り扱いに関する設計方針を徹底
  - 全てのバッチ処理で datetime.today() / date.today() を不用意に参照しない設計（外部から target_date を注入することでルックアヘッドバイアスを防止）。
  - DuckDB の date 値を安全に Python の date オブジェクトに変換するユーティリティを追加。

- データベース操作の安全性強化
  - 各種書き込み処理は BEGIN / DELETE / INSERT / COMMIT の冪等フローで行い、例外時は ROLLBACK を試行して上位へ例外を伝播する方針を採用。
  - DuckDB executemany に対する空リスト回避を明示的に扱う。

### 修正 (Fixed)
- API の堅牢性向上
  - OpenAI 呼び出しでのエラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError の扱い）に応じた再試行/フォールバックロジックを実装。
  - JSON レスポンスの不定形（前後に余計なテキストが混ざる等）に対する復元処理を追加（最外側の {} を抽出して parse を試みる）。

### 注意 / マイグレーション (Notes)
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須（未設定時は ValueError）。
  - OpenAI を使う関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY が必須。未設定時に ValueError を返します。
- 自動的な .env ロードはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp と regime_detector の OpenAI API 呼び出し部分はモジュール内で分離しており、テスト時にモック差し替えしやすい設計になっています（例: unittest.mock.patch）。
- DuckDB のバージョン差異（特に executemany の挙動）に注意。空のパラメータで executemany を呼ばない実装上の配慮が入っています。

### 既知の制限 (Known limitations)
- PBR や配当利回りなど一部のバリューファクターは未実装（将来の拡張予定）。
- OpenAI のレスポンス品質によってはスコア算出が不安定になる可能性があるため、フェイルセーフとして失敗時はスコアをスキップまたは 0.0 にフォールバックする実装になっています。
- calendar_update_job は J-Quants クライアント実装（jquants_client）に依存する。API 側の制約やレスポンス形式変更により影響を受ける可能性があります。

---

今後の TODO / 予定
- 追加のファクター（PBR、配当利回り等）の実装。
- AI モデル切替やローカル評価のための抽象化。
- 単体テスト・統合テストの整備（特に外部 API モックの充実）。
- 監視・アラート機能（Slack 連携など）の強化。

