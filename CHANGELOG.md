# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

- リリースポリシー: 互換性を壊す可能性のある変更はメジャー番号を上げます。  
- バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

### 追加
- （今後の追加項目をここに記載）

---

## [0.1.0] - 2026-04-04
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な機能と設計方針は以下のとおりです。

### 追加
- パッケージ基盤
  - パッケージ初期化とエクスポートを実装（kabusys.__init__）。主要サブパッケージを公開: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数/.env 読み込みユーティリティを追加（kabusys.config）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない .env 自動読み込みを実装。
    - .env / .env.local の読み込み優先順位（OS環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - export KEY=val 形式、引用付き値のエスケープ処理、インラインコメント対応などに対応する堅牢な .env パーサを実装。
    - settings オブジェクトを提供し、必要な設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）やデフォルト値（DB パスや監視閾値など）をプロパティ経由で取得可能に。

- AI（自然言語処理）関連
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini、JSON モード）へバッチ送信し、ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたりの記事/文字上限、レスポンスの厳格なバリデーション（JSON 抽出、results 構造、コード照合、スコア数値化）などを実装。
    - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフとリトライを実装。その他のエラーはスキップして処理継続（フェイルセーフ）。
    - API 呼び出し部分はテスト容易性のため _call_openai_api を抽象化し、テストで差し替え可能。
    - lookahead バイアス回避のため datetime.today() を参照せず、ターゲット日ベースでウィンドウを計算。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせ、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは独立実装（news_nlp と結合しない）で、API エラー時はマクロセンチメントを 0.0 にフォールバック。
    - リトライ・バックオフ、JSON パース保護、ルックアヘッド防止設計を採用。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインのインターフェースと結果データクラス（kabusys.data.pipeline.ETLResult）を実装。
    - ETL 実行の取得数／保存数、品質チェック結果、エラー一覧などを保持し、辞書化可能（監査ログ用）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを提供。
    - データがない場合の曜日ベースフォールバック（週末除外）、DB 値優先の一貫した挙動、最大探索制限で無限ループを回避。
    - J-Quants API からの夜間バッチ更新ジョブ（calendar_update_job）とバックフィル・健全性チェックを実装。
  - ETL 実装方針に沿った差分取得・保存・品質チェックの基盤を整備（jquants_client と quality モジュールを利用する想定）。

- リサーチ用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1/3/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、流動性指標）、Value（PER、ROE）を DuckDB SQL ベースで実装。
    - データ不足時の None ハンドリング、営業日ベースのホライズンスキャン、効率的なウィンドウ集計を考慮。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク変換ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（pandas など未使用）。

### 変更（設計上の決定／注意点）
- DuckDB 互換性
  - DuckDB の executemany が空リストを受け付けないバージョン（例: 0.10）への互換性確保のため、実際に executemany を呼ぶ前にパラメータリストが非空であることをチェックする実装を行っています（ai_scores の書き込みなど）。
- 日付・時刻取り扱い
  - すべての分析・スコア計算でルックアヘッドバイアスを防ぐため、内部で datetime.today()/date.today() を直接参照しない設計。target_date を明示的に渡して処理を行います。
  - ニュースウィンドウは JST を基準に計算し、DB 比較用に UTC naive datetime で扱う（calc_news_window 実装）。
- OpenAI 統合
  - モデルは gpt-4o-mini を想定し JSON Mode を利用する設計（response_format の JSON オブジェクト指定）。
  - レスポンスの厳格なバリデーションとパース後の安全な値クリッピング（±1.0）を実施。
  - API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出することで明確にエラーを通知。

### 修正（堅牢性向上）
- .env 読み込みでのファイル読み込み失敗を warnings.warn で通知し、プロセスを停止させないように実装。
- データ不足や API エラー時には例外でプロセス全体を止めずにフェイルセーフ（デフォルト値やスキップ）で継続するよう取り扱いを統一。
- DB 書き込みは冪等（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）を基本とし、ROLLBACK 失敗時は警告ログで明示。

### 既知の制約 / 注意事項
- OpenAI 呼び出しは外部ネットワーク依存のため、API 利用制限やコストに注意してください。API 呼び出し失敗時は部分的にデータが更新されない場合があります（設計上は部分失敗で既存データを保護するよう配慮済み）。
- raw_financials の一部指標（PBR・配当利回り）は現バージョンでは未実装。
- jquants_client、quality モジュールなど外部依存部分は実行環境で提供されていることが前提です。
- テスト時の自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

メンテナンスやバグ修正、将来的な機能追加はこの CHANGELOG に逐次追記します。