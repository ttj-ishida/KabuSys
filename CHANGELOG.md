# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

- リリースノートは機能追加・変更・修正の観点で記載しています。
- 日付は本コードベースの現行バージョン（__version__ = 0.1.0）に合わせて記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-01
初回公開リリース。日本株自動売買・データ基盤・リサーチ・AI支援の基盤機能を実装しました。

### 追加 (Added)
- パッケージの基本情報
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ に公開）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装：
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの実装（コメント行、export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメント処理）。
  - 環境変数上書きロジック（override フラグ）と OS 環境変数保護（protected set）。
  - Settings クラスを実装し、J-Quants・kabuステーション・Slack・DBパス・監視閾値・環境・ログレベル等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値で ValueError を送出）。

- AI モジュール (src/kabusys/ai/)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事・文字数制限、JSON Mode を利用した応答処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（results リスト・code/score 検証、スコアのクリップ）。
    - 書き込みは idempotent（部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部分をモックしやすい設計（内部 _call_openai_api を patch 可能）。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ計算）を実装。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - DuckDB の prices_daily / raw_news を参照し、ma200_ratio 計算、マクロ記事抽出、OpenAI API 呼び出し、スコア合成、market_regime へ冪等書き込みを行う。
    - API 呼び出し失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ。
    - API 呼び出しはリトライ・バックオフ対応、JSON パースエラーを抑制して継続。
    - テストしやすさのため _call_openai_api を差し替え可能に設計。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - Volatility / Liquidity: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金（avg_turnover）、volume_ratio を計算。
    - Value: raw_financials から EPS/ROE を取得し PER/ROE を算出（EPS が 0/欠損の場合は None）。
    - DuckDB SQL ウィンドウ関数を使った効率的実装。データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターンの計算（calc_forward_returns: 任意 horizon に対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンランク相関 calc_ic）。
    - ランク関数（rank）: 同順位は平均ランク、浮動小数丸め対策を実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データ基盤 (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）: J-Quants から差分取得 → 市場カレンダーを冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar 未取得時の曜日ベースフォールバック（週末は非営業日）、DB 登録値優先の一貫した振る舞い。
    - 探索上限 (_MAX_SEARCH_DAYS) により無限ループを防止、バックフィル・健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し、ETL の取得/保存件数や品質問題・エラーを集約可能に。
    - 差分更新・バックフィル・品質チェック設計に対応（jquants_client と quality モジュールを利用する想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 互換性・運用関連
  - DuckDB を前提とした SQL 実装（executemany の空リスト扱い等、DuckDB の既知制約に配慮した実装）。
  - OpenAI SDK（OpenAI クライアント）を使用。API キーは引数注入 or 環境変数 OPENAI_API_KEY で指定。
  - Slack 通知用の設定項目（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）を Settings に定義。
  - デフォルトの DB パス（duckdb / sqlite）、PID ファイルパス、監視閾値などのデフォルト値を提供。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- OpenAI 呼び出しは課金が発生するため、本番運用時は API キー管理に注意が必要です。API の障害やレート制限はフェイルセーフでスコア 0.0 にフォールバックしますが、品質面の考慮を行ってください。
- 一部関数はデータ不足（過去データが未整備）時に None を返す設計です。上位処理でのハンドリングが必要です。
- DuckDB のバージョン差異により引数バインドや executemany の挙動が異なるため、その点に配慮して実装されています。
- datetime.today()/date.today() の直接参照は避け、関数呼び出し側で target_date を明示的に渡す設計にしているため、ルックアヘッドバイアス防止が図られています。
- jquants_client / quality モジュールや jquants API 連携部分は抽象化されており、実際の接続情報・認証は環境変数や外部設定で提供する必要があります。

---

今後のリリースでは、運用監視・発注実行・Slack 通知・テストカバレッジ・ドキュメントの追加などを予定しています。