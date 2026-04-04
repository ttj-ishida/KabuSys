# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
リリース日付はコードベースから推測できる最新版の日付を記載しています。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-04
初期リリース（推定）。日本株自動売買・データ基盤・研究用ユーティリティ群を含む最初の公開バージョン。

### 追加（Added）
- パッケージ概要
  - 基本パッケージ名: kabusys（日本株自動売買システムのコアライブラリ）。
  - バージョン定義: __version__ = "0.1.0"。

- 環境変数/設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
  - .env パーサを独自実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮）。
  - 自動読み込みの抑止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 上書きポリシー: OS 環境変数を保護する protected 機構、.env と .env.local の読み込み優先度制御（.env.local が上書き）。
  - Settings クラス（settings インスタンス）により各種設定をプロパティ経由で取得:
    - J-Quants / kabu API / LINE / DB パス（DuckDB/SQLite）/監視設定（PIDファイル・killフラグ等）/システム環境（KABUSYS_ENV, LOG_LEVEL）など。
  - 環境変数検証:
    - 必須キー未設定時は ValueError を送出（_require）。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（不正値は ValueError）。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - raw_news と news_symbols から銘柄ごとの記事を集約して LLM（gpt-4o-mini）でセンチメント評価し ai_scores に書き込むワークフローを実装。
    - タイムウィンドウ計算（JST ベース → UTC に変換）を提供（calc_news_window）。
    - 1銘柄あたり記事数・文字数上限（バッチ／トリム）を採用しトークン爆発を抑止。
    - 最大バッチサイズ、エクスポネンシャルバックオフ（429/接続断/タイムアウト/5xx を対象）によるリトライ実装。
    - レスポンスの厳密な JSON 検証・パースおよびスコア数値化・±1.0 クリッピング。
    - DuckDB の executemany の制約（空リスト不可）を考慮した安全な DB 書き込み（DELETE→INSERT、部分失敗時に既存スコアを保護）。
    - テスト用フック: API 呼び出し用の内部関数を patch 可能にしてユニットテストを容易化。

  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルに書き込む実装。
    - MA200 のルックアヘッド回避（target_date 未満データのみ使用）。
    - マクロ記事抽出はキーワードベースでフィルタし、LLM 呼び出しは記事がある場合のみ実施。
    - OpenAI SDK（OpenAI クライアント）を用いた JSON mode 呼び出し。失敗時は macro_sentiment = 0.0 でフェイルセーフ継続。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外発生時の ROLLBACK の試行。
    - API 呼び出し用の内部関数を patch 可能にしてユニットテストを容易化。

- 研究用モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）および流動性指標の計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用した高効率実装。データ不足時は None を返す設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズン）calc_forward_returns。
    - IC（Spearman ランク相関）計算 calc_ic（結合・欠損除外・最小サンプルチェックあり）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定、next/prev/get_trading_days、is_sq_day などのユーティリティ。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末非営業）を採用。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得し保存（バックフィル、健全性チェックを実装）。
    - 最大探索日数やバックフィル日数などの安全措置を導入。
  - ETL / パイプライン（pipeline, etl）
    - ETL の結果を表現する ETLResult データクラスを公開。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定した設計。エラー・品質問題は収集して呼び出し元に委ねる挙動。
    - DuckDB テーブル存在チェックなどのユーティリティ実装。

- 実装上の注意・設計方針（全体）
  - ルックアヘッドバイアス防止: いずれの主要処理（ニュース/レジーム/ETL/研究系）も内部で datetime.today()/date.today() を参照しておらず、明示的な target_date 引数を使用。
  - DuckDB を主要ストレージとして利用（DuckDB のバージョン差異に配慮した実装コメントあり）。
  - OpenAI モデル: gpt-4o-mini を想定して JSON mode を利用。
  - テスト容易性: 外部 API 呼び出し（OpenAI）部分は内部関数を patch できるように分離。

### 変更（Changed）
- なし（初回リリースのため）。

### 修正（Fixed）
- なし（初回リリースのため）。

### 既知の制限 / 注意事項（Notes）
- 外部依存:
  - DuckDB と OpenAI Python SDK（およびネットワーク接続）が必要。
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要がある。未設定時は ValueError を送出する箇所がある。
- DB 書き込みは DuckDB の実装差異（例: executemany の空リスト不可）に配慮した対応済みだが、実運用時の DuckDB バージョン互換性を確認すること。
- 一部ログや挙動は本番運用前に設定（環境変数や DB 初期化）の検証が必要。
- top-level パッケージ公開名・サブパッケージの完全な公開 API （strategy, execution, monitoring 等）については、実装の有無と照合して運用すること。

### セキュリティ（Security）
- なし（このリリースで特記すべき脆弱性は確認されていません）。

---

（この CHANGELOG はリポジトリ内のソースコードから機能・設計方針を推測して作成しています。細部は実際のコミット履歴やリリースノートと差異がある可能性があります。）