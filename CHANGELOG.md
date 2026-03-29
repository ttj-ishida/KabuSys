# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

最新リリース: 0.1.0 (初期リリース)

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買システム「KabuSys」のコアライブラリ群を実装します。主な追加点は以下の通りです。

### 追加
- パッケージ初期化
  - `kabusys` パッケージを導入。バージョンは `0.1.0`。

- 環境設定管理（kabusys.config）
  - .env ファイル / 環境変数から設定を読み込む `Settings` クラスを提供。
  - 自動 .env ロード機構を実装（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサを実装（`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行コメント処理等に対応）。
  - 必須環境変数の取得ヘルパ（`_require`）と各種プロパティを提供:
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ ログレベル判定など。
  - 環境値のバリデーション（有効な env 値、ログレベルのチェック等）。

- AI 関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を用い銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）に基づく記事集約。
    - 1 銘柄あたり最大記事数・文字数のトリミング実装（トークン肥大化対策）。
    - BATCH 処理（最大 20 銘柄/リクエスト）で効率的に取得。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライの実装。失敗時はスキップして処理継続（フェイルセーフ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト回避ロジック）。
    - テスト容易性のため OpenAI 呼び出しをモック差し替え可能（内部関数の参照方法を明示）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を組み合わせ、日次で市場レジーム（"bull"/"neutral"/"bear"）を判定。
    - マクロニュース抽出に使うキーワード群を定義（日本・米国・グローバル関連語）。
    - LLM 呼び出しは JSON モードで行い、レスポンスの JSON パースに失敗した場合は macro_sentiment = 0.0 でフォールバック。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と待機時間（指数バックオフ）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止設計（target_date 未満のデータのみ参照、datetime.today() を直接参照しない）。

- データ管理（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを保持する `market_calendar` を扱うユーティリティを提供。
    - 営業日判定関数群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値が存在する場合は DB を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジックを採用。
    - 最大探索日数制限（無限ループ防止）や健全性チェックを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装：J-Quants から差分取得→冪等保存（save_market_calendar 経由）→バックフィル処理。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表す `ETLResult` データクラスを提供（取得数・保存数・品質問題・エラーなどを集約）。
    - 差分更新ロジック、バックフィル、品質チェックの考慮（品質問題は収集して上位で判断する設計）を想定したインターフェースを提供。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、トレーディングデー調整など。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER, ROE）を DuckDB 経由で計算する関数群を実装。
    - データ不足時の None 扱い、結果は (date, code) を含む辞書リストで返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient、Spearman rank）計算（calc_ic）。
    - 値をランクに変換するユーティリティ（rank）。
    - 統計サマリー（factor_summary）による count/mean/std/min/max/median の算出。
  - 便利関数や再利用可能なインターフェース（`zscore_normalize` を data.stats から再エクスポート）。

### 改善（設計上の注意・堅牢化）
- DuckDB を主要なローカル DB として採用し、SQL ウィンドウ関数を活用した効率的な集計を実装。
- API 呼び出し周りは失敗時に例外をそのまま上げない（ログ記録してフォールバック）方針により、バッチ処理での堅牢性を重視。
- JSON Mode を使った LLM レスポンスの厳密な期待値に対し、不正レスポンス（前後余分なテキスト等）を復元してパースする耐性を実装。
- テスト容易性を考慮し、内部での OpenAI 呼び出しポイントを差し替え可能に設計。

### 既知の制約 / 注意点
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要がある。未設定時は ValueError を送出する設計。
- ai/news_nlp/regime_detector は実際に OpenAI へ問い合わせを行うため、API 使用に伴うコストとレート制限に注意が必要。
- 一部 DuckDB のバージョン依存（executemany の空リストバインド等）に対応するワークアラウンドを実装しているが、環境差異により挙動が変わる可能性あり。
- 現時点で実装されているのは分析・データ処理ロジックとバッチ保存ロジックであり、実際の売買発注・実行部分（execution 等）は本差分からは確認できない（将来のモジュール上で取り扱う想定）。

---

今後の予定（例）
- execution モジュールの実装（オーダー発注・約定管理）と安全対策の強化
- 監視 / アラート機能（monitoring）の強化、Slack 通知の統合テスト
- ai モデルのプラガブル化（モデル切替・少量微調整のサポート）
- ETL の品質チェックルール追加とレポーティング機能の充実

(以上)