Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 — 2026-03-31
-------------------

Added
- 初期リリースとして以下の主要モジュールを追加。
  - kabusys パッケージのエントリポイントとバージョン管理（__version__ = "0.1.0"）。
  - 環境設定管理（kabusys.config）
    - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ から .git または pyproject.toml を探索して特定（CWD に依存しない挙動）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 環境変数を保護するため .env ロード時に既存キーを保護（.env.local は override）。
    - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス等のプロパティ。値検証・必須チェックを含む）。
    - KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装し、不正値時は例外を送出。

  - AI モジュール（kabusys.ai）
    - news_nlp.score_news
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores に書き込む。
      - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30 → UTC に変換）に基づく記事抽出。
      - 1 銘柄あたりの記事数・文字数制限（肥大化対策）。
      - バッチサイズ、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
      - レスポンスの厳密なバリデーション（JSON モードの余剰テキスト対応、結果構造・コード照合・数値検証）。
      - 部分成功時の DB 書き換え戦略（該当コードのみ DELETE → INSERT）により既存データ保護。
      - テスト容易性: OpenAI 呼び出しを差し替えられる（内部 _call_openai_api に patch 可能）。

    - regime_detector.score_regime
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で保存。
      - マクロニュースは news_nlp.calc_news_window を使って期間を決定し、キーワードでフィルタして LLM に投げる。
      - OpenAI の呼び出しに対してリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
      - ルックアヘッドバイアス防止の設計（datetime.today() を直接参照しない、DB クエリは target_date 未満の制約）。

  - Data モジュール（kabusys.data）
    - calendar_management
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day をサポート。
      - DB 登録がない日には曜日（平日）ベースのフォールバックを採用し、DB と一貫した挙動。
      - カレンダー夜間バッチ（calendar_update_job）: J-Quants から差分取得・バックフィル・健全性チェック・保存処理を実装。
    - pipeline / ETL
      - ETLResult データクラスと ETL の補助ユーティリティ（最終取得日の検出、テーブル存在チェック等）。
      - 差分取得、バックフィル、品質チェック（quality モジュールへの連携）を想定した設計。
      - idempotent な保存（ON CONFLICT 相当）を前提にした保存フローを想定。
    - etl を公開インターフェースとして再エクスポート。

  - Research モジュール（kabusys.research）
    - factor_research
      - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）等のファクター計算を実装。
      - DuckDB を用いた SQL ベースの計算（prices_daily, raw_financials 参照）。
      - データ不足時の None ハンドリング。
    - feature_exploration
      - 将来リターン計算（任意ホライズン）、IC（Spearman rank correlation）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
      - 外部依存を持たない純標準ライブラリ + duckdb 実装。
    - zscore_normalize を含むデータユーティリティと併せて再エクスポート。

Changed
- （初版のため "Changed" は該当なし。ただし設計上の注意点やデフォルト挙動を明記）
  - 多くの箇所で「ルックアヘッドバイアス防止のため日付取得に datetime.today()/date.today() を直接使わない」設計を採用。
  - OpenAI 呼び出し回りは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを重視。
  - DuckDB の executemany に関する互換性を考慮した実装（空リスト送信回避）。

Fixed
- （初版のため "Fixed" は該当なし）

Security
- 環境変数読み込み時に既存 OS 環境変数を保護する仕組みを導入（.env による意図しない上書きを防止）。
- OpenAI API キー等の必須値が未設定の場合は ValueError を送出して明示的にエラーを通知。

Notes / 実装上の重要な挙動
- DB 書き込みは基本的にトランザクション（BEGIN / DELETE / INSERT / COMMIT）を使用し、失敗時は ROLLBACK を試みる。ROLLBACK に失敗した場合はログ出力。
- OpenAI API 呼び出しはリトライ戦略を採用（指数バックオフ）。ただし永続的な失敗はフェイルセーフとしてゼロスコアやスキップで継続する設計。
- news_nlp と regime_detector は内部で OpenAI 呼び出し関数を独立実装しており、モジュール間でプライベート関数を共有しない方針（テスト容易性とモジュール分離を重視）。
- タイムゾーン: raw_news 等は UTC で保存されている前提。ニュースウィンドウ計算は JST 基準→UTC 変換を行う（naive datetime を使用）。
- テスト向けの注入ポイント:
  - API キーは関数引数で注入可能（api_key 引数）。None の場合は環境変数 OPENAI_API_KEY を参照。
  - OpenAI 呼び出しは内部関数（_call_openai_api）を unittest.mock.patch により差し替え可能。

互換性 / マイグレーション
- v0.1.0 は初期リリースのため互換性の過去バージョンは存在しません。今後のバージョンで API 変更を行う場合は Breaking Changes を本ファイルで明示します。

Contributors
- 初回実装（多数のサブモジュールとユーティリティを含む）により構成。

（以上）