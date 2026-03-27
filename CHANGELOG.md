# CHANGELOG

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 今後の予定（コードから推測）
  - ファクター群に PBR / 配当利回りを追加実装（現バージョンでは未実装）。
  - さらなる単体テストの追加（OpenAI 呼び出しのモックを活用したテスト拡充）。
  - ETL の部分失敗時のロギング・リトライポリシー強化。
  - J-Quants / kabu API クライアントの拡張とエラーハンドリング強化。

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームのコア機能群を提供します。設計方針として「ルックアヘッドバイアス回避」「データ保存の冪等性」「外部APIのフェイルセーフ化」「DuckDB 互換性」「モジュール分離」を重視しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = 0.1.0、公開 API を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル／環境変数読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - Settings クラスを提供し、必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）やデフォルト値（KABU_API_BASE_URL、DB パス等）を管理。
  - 環境値検証: KABUSYS_ENV の有効値チェック（development/paper_trading/live）、LOG_LEVEL 値チェック。
- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング: score_news を提供（gpt-4o-mini を用いた JSON mode 呼び出し）。
    - ニュース収集ウィンドウ計算（JST ベース → UTC への変換）を提供（calc_news_window）。
    - 銘柄ごとに複数記事を集約しトークン・文字数肥大化対策（記事数上限・文字数トリム）を実装。
    - API 呼び出しはチャンク（最大 20 銘柄）単位で送信、429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ。
    - レスポンスの厳格バリデーションとスコアの ±1.0 クリップを実装。
    - DuckDB の制約（executemany に空リスト不可）への対応（書き込み前に空チェックを実施）。
  - 市場レジーム判定: score_regime を提供
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）で、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック時の安全対策。
- データ処理（Data Platform）
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの操作ユーティリティ、営業日判定（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバックを採用（週末を非営業日扱い）。
    - 夜間バッチ処理 calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分取得 → 保存 → 品質チェック の流れに沿う ETLResult データクラスを提供（詳細な実行結果 / 品質問題 / エラーを含む）。
    - 最終取得日の算出ユーティリティ、テーブル存在確認ユーティリティ等を実装。
    - デフォルトのバックフィル挙動・カレンダー先読み等をサポート。
- リサーチ / ファクター (src/kabusys/research)
  - factor_research モジュール:
    - モメンタム: 1M/3M/6M リターンと 200 日 MA 乖離を計算する calc_momentum。
    - ボラティリティ / 流動性: 20 日 ATR、相対 ATR、平均売買代金、出来高比を計算する calc_volatility。
    - バリュー: raw_financials と prices_daily を組み合わせて PER / ROE を計算する calc_value（PBR・配当利回りは未実装と注記）。
  - feature_exploration モジュール:
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（Information Coefficient）計算 calc_ic、ランク変換ユーティリティ rank、ファクター統計要約 factor_summary を提供。
  - research パッケージ初期公開 API を整備（関数の再エクスポート）。
- テスト・運用面の配慮
  - OpenAI 呼び出し箇所に対して簡単に差し替え可能な内部関数（_call_openai_api）を用意し、ユニットテストでのモックを想定。
  - 外部 API 失敗時に例外を投げずにフォールバックする設計を多数の箇所で採用（フェイルセーフ）。

### 変更 (Changed)
- 設計方針の明示化
  - 主要なモジュールで「datetime.today()/date.today() を直接参照しない」方針を採用し、ルックアヘッドバイアスを防止（target_date を外部から注入して動作）。
  - DuckDB 固有の挙動（executemany 空リスト不可、日付型取り扱い）に配慮した実装になっている旨の注記と対応コードを追加。
- ロギング・エラーハンドリング強化
  - API 失敗時のログ出力とフォールバック値、ロールバック失敗時の警告ログなど、運用での診断を助けるログを充実。

### 修正 (Fixed)
- 外部 API 呼び出し（OpenAI / J-Quants 等）のエラーケースで処理が中断する問題を軽減（リトライ・フェイルセーフの導入により部分失敗で処理継続）。
- .env パーサの不備を想定した堅牢化（クォート内のバックスラッシュ処理やインラインコメントの扱い、export キーワード対応）。

### セキュリティ (Security)
- 環境変数による API キー管理を前提とし、必須キー未設定時は明示的な ValueError を発生させることにより安全な初期化を促進。
- 自動 .env ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テストや CI 環境での意図しないキー漏洩リスクを低減。

---

注記:
- 本 CHANGELOG は提示されたコードベースから実装内容と設計意図を推測してまとめたものです。各項目の詳細は該当ファイルのドキュメンテーション文字列（docstring）やログメッセージに基づいて記載しています。