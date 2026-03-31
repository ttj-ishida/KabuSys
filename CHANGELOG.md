# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 本ファイルは提供されたコードベースから機能・設計意図を推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース。主要な機能群と公開 API を実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化 (kabusys/__init__.py) とバージョン設定 (__version__ = "0.1.0") を追加。
  - 公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境設定/ローダー (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に自動的に探索（CWD 非依存）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、以下のプロパティを提供:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token, slack_channel_id（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 必須）
    - duckdb_path / sqlite_path（デフォルトパスを持つ）
    - env（KABUSYS_ENV の検証、許可値: development / paper_trading / live）
    - log_level（LOG_LEVEL の検証、許可値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ラッパーメソッド: is_live / is_paper / is_dev

- データプラットフォーム関連 (kabusys.data)
  - ETL インターフェースの公開 (ETLResult を再エクスポート)。
  - market_calendar を管理するカレンダーモジュールを実装:
    - 営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）
    - 夜間バッチ更新ジョブ (calendar_update_job) — J-Quants API から差分取得して冪等保存
    - DB データがない場合は曜日ベースのフォールバック（週末を非営業日扱い）
    - 健全性チェック、バックフィル、最大探索日数による無限ループ防止
  - ETL パイプライン基盤 (kabusys.data.pipeline):
    - ETLResult dataclass を実装（取得件数、保存件数、品質問題、エラー等を保持）
    - 差分更新・バックフィル・品質チェックの設計を反映するユーティリティを実装
    - DuckDB の挙動を考慮した実装（例: executemany に空リストを渡さない等）
  - jquants_client 経由でのデータ取得・保存呼び出しを想定（実行は jquants_client に委譲）

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20 日 ATR、ATR 比、20 日平均売買代金、出来高比率を計算
    - calc_value: PER（EPS が 0/欠損時は None）、ROE を raw_financials と prices_daily から計算
    - 設定されたスキャン範囲（バッファ）や欠損時の None 扱い等の設計を反映
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意 horizon）を一度のクエリで取得
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 未満なら None を返す
    - rank: 同順位は平均ランクで扱うランキング実装（丸めで ties 回避）
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）
  - 公開ユーティリティとして zscore_normalize（data.stats から）を再エクスポート

- AI / NLP 機能 (kabusys.ai)
  - ニュースセンチメント（銘柄別）スコアリング (news_nlp.score_news):
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して処理
    - raw_news と news_symbols から銘柄毎に記事を集約（最大記事数 / 最大文字長でトリム）
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）
    - レスポンスは JSON mode 想定。バリデーションと数値クリッピング（±1.0）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - DuckDB 互換性のため、部分書き換え（DELETE → INSERT）で冪等保存。空パラメータを executemany に渡さない保護
    - API キーは引数または環境変数 OPENAI_API_KEY で指定
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせてスコア算出
    - マクロニュースは raw_news をマクロキーワードでフィルタして取得
    - LLM 呼び出しの失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - レジームスコアをクリップし閾値で 'bull' / 'neutral' / 'bear' ラベルを決定
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出し部はモジュール間の結合を避けるため news_nlp とは別実装

### 変更 (Changed)
- なし（初回実装のため）

### 修正 (Fixed)
- なし（初回実装のため）

### セキュリティ (Security)
- なし

### 既知の制約・設計上の注意 (Notes / Known limitations)
- AI 機能は OpenAI API に依存。API キー未設定時は ValueError を送出する（score_news / score_regime）。
- LLM レスポンスのパース・バリデーションを行い、失敗時は該当コードをスキップまたはスコアを 0.0 にフォールバックする設計（例外をサービス全体で上げない方針）。
- 全コードはルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照しない設計。ただし calendar_update_job 内では日次バッチ想定で date.today() を使用。
- DuckDB のバージョン互換性（executemany の空リスト許容性など）を考慮した実装上の回避措置が入っている。
- .env の自動ロードはプロジェクトルート検出に依存。配布後や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御可能。

### 互換性に関する注意 (Breaking Changes)
- なし（初回リリース）

---

今後の予定（非網羅）
- strategy / execution / monitoring サブパッケージの具体的なトレード実行・監視ロジックの実装
- テスト用のモックや CI ワークフローの追加
- より詳細な品質チェック（quality モジュール拡張）と監査ログ強化
- OpenAI 呼び出しの抽象化・プラグイン化（他プロバイダ対応）

もし特定の変更履歴の表現（例: 日付フォーマットやセクション分け）や、より詳細な項目（コミット単位での記載など）を希望される場合は指示してください。