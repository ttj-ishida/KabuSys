# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠します。

なお、このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-01

### 追加 (Added)
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開トップレベルモジュール: data, strategy, execution, monitoring（__all__ により公開）

- 環境設定管理モジュールを実装（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を基準）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応）。
  - protected 実装により OS 環境変数の上書きを保護する読み込みオプションをサポート。
  - Settings クラスを提供し、主要設定のプロパティを取得可能（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値設定、KABUSYS_ENV/LOG_LEVEL の検証など）。

- AI 関連モジュールを追加（src/kabusys/ai/）
  - ニュース NLP スコアリング（score_news）（src/kabusys/ai/news_nlp.py）
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント解析。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - 銘柄ごとに記事を集約して最大文字数・記事数でトリムし、最大 20 銘柄をチャンク処理。
    - レスポンスの厳密なバリデーションと ±1.0 クリッピング。
    - API エラー（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフリトライ。失敗時は該当チャンクをスキップしフェイルセーフで継続。
    - DuckDB への冪等書き込み（DELETE → INSERT）を実装し、部分失敗時に既存データを保護。
  - 市場レジーム判定（score_regime）（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）による JSON レスポンスの取得とパース、API リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 共通設計: OpenAI API 呼び出しはモジュール内で独立実装。テスト時に差し替え可能。

- データ処理モジュール（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを使った営業日判定・次/前営業日取得・期間内営業日列挙・SQ 判定。
    - DB 未登録日の場合は曜日ベース（土日非営業）でフォールバック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得し冪等保存。バックフィル・健全性チェック実装。
  - ETL パイプラインの公開インターフェース（pipeline.py / etl.py）
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラー集約・シリアライズ機能）。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）に関する基本設計を実装。
    - jquants_client 経由の安全な保存（Idempotent 保存）の利用を前提。

- リサーチ / ファクター計算モジュール（src/kabusys/research/）
  - factor_research.py: モメンタム、ボラティリティ、バリュー等の定量ファクター計算（prices_daily / raw_financials のみ参照）。
    - calc_momentum: mom_1m/3m/6m と ma200 の乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
    - calc_value: PER / ROE（最新財務データとの結合）。
  - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、統計サマリー（factor_summary）。
  - research パッケージはデータ統計ユーティリティ（zscore_normalize）と組み合わせて使用する構成。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。ただし以下の設計方針が繰り返し明示されている:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を関数内部で直接参照しない設計（全 AI / ニュース / レジーム / リサーチ機能で共通）。
  - DuckDB を主要なローカル分析 DB として利用し、SQL と Python を組合せたデータ処理。

### 修正 (Fixed)
- なし（初回リリース）。ただし以下の堅牢化が実装されている点を記載：
  - OpenAI 呼び出しのリトライ/バックオフ・エラー種別判定（429・ネットワーク・タイムアウト・5xx）や、API レスポンスのパース失敗に対するフェイルセーフ（デフォルトスコア 0.0、チャンクスキップ）。
  - DuckDB に対する executemany の空リスト制約への対応（空リストを渡さないガードを追加）。
  - .env 解析での引用符・エスケープ・コメント処理を明確化し、一般的な .env フォーマットの互換性を向上。

### セキュリティ (Security)
- セキュリティに関する変更はなし。ただし以下の注意点を明記:
  - API キー（OpenAI / J-Quants / kabu API / Slack）は環境変数経由で取得。Settings は未設定時に ValueError を投げることで安全に失敗する設計。
  - .env 自動読み込みで OS 環境変数を上書きしない（デフォルト）仕様と、明示的な上書き制御（.env.local）をサポート。

---

注記:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合があります。必要であれば、実際のコミット履歴やリリース記録を基に追補／修正してください。