# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリースはセマンティックバージョニングを採用しています。

現在のリリース日付はリポジトリ内のスナップショット（このコードベース）に基づいて推測しています。

## [Unreleased]
- 今後対応予定 / 注意事項
  - data.pipeline._get_max_date の実装末尾に不完全なコード（`date.fro` のような断片）が見られます。これは現状ビルド時にエラーとなる可能性があるため修正予定です。
  - 一部のパッケージ公開（例: strategy, execution, monitoring）が __all__ に列挙されているものの、このスナップショットに詳細実装が含まれていません。これらは継続開発・追加予定です。

---

## [0.1.0] - 2026-04-01

初回公開リリース（ベース機能群の実装）。以下の機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加。バージョンは 0.1.0。
  - サブパッケージとして data / research / ai / (予定: strategy, execution, monitoring) をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（ファイル位置ベースで CWD に依存しない）。
  - .env パーサの強化:
    - 空行・コメント（#）の扱い、export プレフィックスのサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値の末尾コメント認識（直前がスペース/タブの場合にのみ）。
  - .env 自動ロードの優先順位: OS 環境変数 > .env > .env.local（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB / SQLite）/ 監視閾値 / ログ・環境フラグ など
  - 入力検証の実装:
    - KABUSYS_ENV, LOG_LEVEL の許容値チェック
    - 必須環境変数未設定時に ValueError を送出する _require の導入

- AI（自然言語処理）関連 (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（JST基準 → DB比較用にUTC naive datetimeで返却）：calc_news_window を実装。
    - バッチ処理（1回あたり最大20銘柄）・1銘柄あたりの最大記事数・最大文字数でトリム。
    - JSON Mode を利用した厳密な JSON レスポンス期待と、レスポンスの堅牢なバリデーション実装（_validate_and_extract）。
    - エラー耐性: 429、ネットワーク断、タイムアウト、5xx は指数バックオフでリトライ。その他はスキップ。API失敗時は例外を投げずフェイルセーフにフォールバック。
    - DuckDB への冪等書き込み（DELETE → INSERT の順）と、部分失敗時に既存データを保護する設計。
    - テスト容易性: _call_openai_api をユニットテストで patch 可能。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム判定（bull / neutral / bear）を実装。
    - マクロニュースは news_nlp.calc_news_window に基づいたウィンドウで抽出し、OpenAI を用いて macro_sentiment を評価。
    - LLM 呼び出しは専用実装でモジュール分離。API 再試行ロジックとフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス回避を重視（date.today() を参照しない、DB クエリは target_date 未満の排他条件）。

- リサーチ（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research:
    - モメンタム: 約1M/3M/6M リターン（営業日ベース）、200日移動平均乖離（ma200_dev）。
    - ボラティリティ: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: PER（EPSが0または欠損時は None）、ROE（raw_financials からの最新値）。
    - DuckDB SQL を活用した効率的な実装。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns（デフォルト horizons=[1,5,21]）、単一クエリで複数ホライズンを取得。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関）、3件未満で None を返す。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めで ties 検出の安定化）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
  - zscore_normalize は kabusys.data.stats から再公開。

- データプラットフォーム / ETL / カレンダー管理 (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存（バックフィル / 健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧などを含む）。
    - ETL の差分更新、バックフィル、品質チェック（quality モジュールとの連携）方針を実装。
    - jquants_client を通じたデータ取得/保存を前提とした差分取得ロジックを実装（詳細は jquants_client 実装に依存）。

- インフラ・依存
  - DuckDB を主要なストレージ・分析 DB として利用。
  - OpenAI（gpt-4o-mini）との連携を前提とした設計（JSON Mode、リトライ、フェイルセーフ）。
  - Slack 通知用トークン/チャンネル ID を Settings で管理（将来のモニタリング機能に利用予定）。

### 変更 (Changed)
- （初期リリース）内部設計に関するドキュメント的注記を多数追加：
  - ルックアヘッドバイアス防止（datetime.today() を参照しない）等の設計方針を各モジュールの docstring に明記。
  - DuckDB の executemany の制約（空リスト不可）に配慮した実装。

### 修正 (Fixed)
- N/A（初版）。

### セキュリティ (Security)
- 必要な機密情報（OpenAI API キー、Slack トークン、Kabu API パスワード、J-Quants トークン等）は環境変数経由で管理する設計。CHANGELOG は機密情報を含みません。

### 既知の問題 (Known issues)
- data/pipeline._get_max_date の末尾に不完全なコード片が見つかります（このままでは実行時エラーの原因）。要修正。
- strategy / execution / monitoring の具象実装がスナップショットに含まれていないため、実際の発注・監視ワークフローは未完成。
- .env パーサは多くのケースに対応していますが、極端に複雑なシェル展開（変数展開やコマンド置換）には非対応です。

---

メンテナンス／開発方針の目安
- 外部 API 呼び出しはフェイルセーフ（失敗しても全体が停止しない）を基本とする。
- ルックアヘッドバイアス対策を徹底（日時の取り扱いは明示的に target_date を渡す）。
- DuckDB の互換性（executemany 等）を考慮した実装を優先。
- ユニットテストでは OpenAI 呼び出し部分を patch して差し替え可能な設計を維持。

（必要であればこの CHANGELOG をリポジトリの状態に合わせて日付・項目を微調整します。）