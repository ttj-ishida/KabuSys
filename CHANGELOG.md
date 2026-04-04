# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
このプロジェクトはまだ初期バージョンであり、安定性・API が変わる可能性があります。

全般
- 日付形式: YYYY-MM-DD
- 現在のパッケージバージョン: 0.1.0（src/kabusys/__init__.py）

## [Unreleased]
今後の予定/着手予定の事項（コードベースから推測）:
- strategy / execution / monitoring の具体実装の追加（パッケージの __all__ に含まれるが、今回のスナップショットでは未提示）。
- 監視・実行周りの統合テスト、デプロイ用ドキュメントの整備。
- jquants_client の外部依存周り（認証や API の差分取得ロジック）に関する拡張。
- モデルやプロンプトのチューニング、OpenAI 呼び出しに対するコスト制御やキャッシュ機能の追加。

---

## [0.1.0] - 2026-04-04

初回リリース — 基本的なデータパイプライン、リサーチユーティリティ、AI ベースのニュース解析・レジーム判定機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、バージョン 0.1.0）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含める（将来実装を想定）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml ベース）。
  - .env と .env.local の読み込み優先度を実装（OS環境変数 > .env.local > .env）。
  - export KEY=val 形式、クォート／エスケープ、インラインコメントの扱い等を考慮した .env パーサーを実装。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数検査 (_require) と Settings クラスによる型付きアクセスを提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, 環境・ログレベル検証 等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と利便性プロパティ（is_live / is_paper / is_dev）を実装。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols から銘柄別ニュースを集約し、OpenAI（gpt-4o-mini / JSON Mode）で銘柄ごとのセンチメントスコアを計算して ai_scores に保存するワークフローを実装。
  - ニュース収集ウィンドウの計算（JST基準 → UTC naive datetime）calc_news_window を提供。
  - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事数/文字数の上限トリム、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ等を実装。
  - エラーハンドリング: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、その他のエラーはスキップして継続するフェイルセーフ設計。
  - テスト容易性のため _call_openai_api を patch で差し替えられる設計。
  - DuckDB への書き込みは冪等性を考慮（DELETE → INSERT、executemany 前に空チェック）して実装。

- AI / 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
  - マクロニュース抽出（キーワードによるフィルタ）、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力解析、リトライ・フェイルセーフロジックを実装。
  - API キー注入（引数 or 環境変数 OPENAI_API_KEY）をサポート。
  - 日付ルックアヘッドバイアス防止のため、内部で datetime.today() を参照しない設計。

- データプラットフォーム / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダー管理ロジックを実装（market_calendar テーブル読み書き、営業日判定、next/prev/get_trading_days、SQ日判定）。
  - DB データ優先だが、DB 未登録日は曜日ベースでフォールバックする一貫した仕様。
  - 夜間バッチ update job (calendar_update_job) を実装。J-Quants API から差分取得・バックフィル機能を組み込み。
  - 健全性チェック（未来日付が不正に遠い場合のスキップ）・最大探索日数保護を実装。

- データプラットフォーム / ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
  - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラーリスト等を保持）。
  - ETL の設計方針に基づく差分更新・バックフィル・品質チェックのためのユーティリティを追加（テーブル存在確認、最大日付取得などの基盤）。
  - 外部 jquants_client と quality モジュールを利用する設計（save_* / fetch_* を想定）。

- 研究用ユーティリティ (src/kabusys/research/)
  - factor_research モジュールにてモメンタム・ボラティリティ・バリュー（per, roe）計算関数を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日 MA 乖離）を計算
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算
    - calc_value: raw_financials 結合による PER / ROE を計算
  - feature_exploration モジュールにて将来リターン計算・IC 計算・統計サマリーを実装:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: Spearman（ランク）を用いた IC（Information Coefficient）計算
    - rank / factor_summary: ランク化・基本統計量集計ユーティリティ
  - 研究ユーティリティは DuckDB を直接参照し、外部 API や取引執行にはアクセスしない安全な設計。

- パッケージ再エクスポート・モジュール整理
  - src/kabusys/ai/__init__.py で score_news をエクスポート。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
  - src/kabusys/data/etl.py で ETLResult を外部に公開。

### 変更 (Changed)
- 初期リリースにあたり、各モジュールは保守性を重視した設計となっており、以下のポリシーを適用:
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB の互換性問題（executemany の空リストバインドなど）を回避するコードパスを採用。
  - OpenAI 呼び出しはモジュールごとに独立したラッパー実装にしてテスト容易性を確保（patch で差し替え可能）。

### 修正 (Fixed)
- 初期公開のための安定化（ログ出力、警告、例外ハンドリングを明示的に実装）。
- .env 読み込みでのファイルアクセスエラーを warnings.warn で通知しプロセス継続できるように修正。

### セキュリティ (Security)
- API キーは引数で注入可能（テスト用）、また環境変数からの取得をデフォルトとして安全な取り扱いを想定。
- .env 読み込み時に既存の OS 環境変数を保護する仕組み（protected set）を実装。

### 既知の制約 / 注意点
- OpenAI / J-Quants クライアント（外部 API）はこのスナップショットでの実装呼び出しを想定しているが、実働には有効な API キーとネットワーク環境が必要。
- 一部モジュール（jquants_client の中身、strategy/execution/monitoring の実体）はスナップショット内に含まれていないため、実運用前にそれらの実装・設定が必要。
- DuckDB のバージョン相違による SQL バインド挙動に留意（executemany の空引数など）。
- AI レスポンスのパース失敗時はフェイルセーフで 0.0 を返すよう設計しているため、部分的に情報欠落が起きてもプロセスは継続するが、結果精度に影響する可能性あり。

---

著者: コードベースの内容から推測して自動生成  
注: この CHANGELOG は与えられたソースコードから機能・設計方針を推測して作成しています。実際の開発履歴やコミットメッセージとは差異がある可能性があります。必要であればコミット履歴に基づく詳細な CHANGELOG を別途生成します。