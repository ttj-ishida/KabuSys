# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に従っています。なお、記載内容は提供されたコードベースから推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買・データ基盤向けユーティリティ群を提供します。主な追加機能・モジュールは以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージ初版を公開。パッケージバージョンは 0.1.0。

- 環境設定 / config
  - .env ファイル（および .env.local）の自動読み込み機能を実装。プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、作業ディレクトリに依存しない挙動を実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の堅牢なパーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理など）。
  - OS 環境変数を保護する上書きポリシー（.env.local は既存 OS 環境変数を保護しつつ上書き可能）。
  - Settings クラスを追加。J-Quants / kabu API / LINE / データベース / 監視 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）を環境変数から取得するプロパティを提供し、値検証（許容値チェック）を実装。

- AI（自然言語処理）関連
  - kabusys.ai.news_nlp
    - news のタイムウィンドウ計算（calc_news_window）とニュース単位でのセンチメントスコアリング（score_news）を実装。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すバッチ処理を実装。銘柄ごとに記事を集約して最大バッチサイズで送信、結果を ai_scores テーブルへ冪等的に保存。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンス検証、スコア ±1.0 クリップ、失敗時はスキップ（フェイルセーフ）などを実装。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - LLM 呼び出しは独立実装とし、API エラー時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。

- データ基盤（Data）
  - kabusys.data.calendar_management
    - JPX カレンダー管理ユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックし、一貫した探索ロジックを実装。
    - calendar_update_job により J-Quants API から差分取得 → 保存（jquants_client 経由）する夜間ジョブを実装。バックフィル・健全性チェックあり。
  - kabusys.data.pipeline / ETL
    - ETLResult データクラスを追加（ETL の取得数 / 保存数 / 品質問題 / エラー一覧などを集約）。
    - pipeline モジュールで差分更新・保存・品質チェックの設計方針を定義（実装の主要方針がコード内で明示）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（Research）
  - kabusys.research.factor_research
    - モメンタム（calc_momentum：1M/3M/6M リターン、ma200 乖離）、ボラティリティ/流動性（calc_volatility：20日 ATR、avg_turnover、volume_ratio）、バリュー（calc_value：PER, ROE）計算関数を追加。DuckDB を活用した SQL ベースの実装。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）および rank / factor_summary 等の探索用ユーティリティを追加。
    - 外部依存（pandas 等）を使わず標準ライブラリと DuckDB のみで実装。

- その他
  - API レベルでの入力検証、エラー時のログ出力、DuckDB の互換性考慮（executemany の空リスト回避等）やルックアヘッドバイアス対策（date.now を直接参照しない設計）が随所に組み込まれている。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- DB 書き込み処理で冪等性を確保するため、market_regime / ai_scores へは DELETE→INSERT のパターンを採用し、BEGIN/COMMIT/ROLLBACK による例外時の整合性保護を実装。
- OpenAI SDK のバージョン差や APIError の status_code 存在有無に対する耐性を追加（getattr を用いた安全な参照等）。

### セキュリティ (Security)

- OpenAI API キーが未設定の場合は明示的に ValueError を送出し、意図しない API 呼び出しを防止。
- 環境変数取得時に必須キー未設定を検出するヘルパ（_require）を備え、起動時の設定漏れを早期に検出。

### 設計上の注記（重要）

- ルックアヘッドバイアス防止のため、各日次処理は必ず引数の target_date に基づく設計（datetime.today()/date.today() を直接参照しない）。
- OpenAI 呼び出しは JSON mode を利用しレスポンス整形を想定。LLM の不安定応答に対してはレスポンスバリデーションとフォールバックロジックを備える。
- DuckDB を主要なオンディスクデータストアとして想定しているため、executemany 等のバージョン差にも配慮した実装になっている。
- API 呼び出し失敗時は原則スキップして処理を継続するフェイルセーフ方針（部分失敗時に既存データを不必要に消さない工夫あり）。

---

この CHANGELOG はコードベースから機能・設計を推定して作成しています。実際のリリースノートや変更履歴と差異がある場合は、差分を反映して更新してください。