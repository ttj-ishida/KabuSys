# B. 初期導入 — WebManual

- **対象**: KabuSys を初めてセットアップする管理者・構築担当者
- **想定読者**: PC 操作・Python 環境の基本的な知識がある方
- **目的**: 環境構築・設定・データ準備を完了し、システムを起動できる状態にする

---

## B-0. 導入前の準備（必須アカウント・ソフトウェア）

KabuSys を動かすには以下がすべて揃っている必要があります。

### 必須アカウント

| アカウント | 用途 | 取得先 |
|---|---|---|
| auカブコム証券 口座 | 実際の発注先 | [auカブコム証券](https://kabu.com/) |
| J-Quants API | 市場データ取得 | [J-Quants](https://jpx-jquants.com/) |

### 必須ソフトウェア

| ソフトウェア | 用途 | 入手方法 |
|---|---|---|
| kabuステーション® | 発注用ローカル API サーバー | auカブコム証券マイページからダウンロード |
| Python 3.11 以上 | システムの実行環境 | [python.org](https://www.python.org/) |
| Git | ソースコード管理 | [git-scm.com](https://git-scm.com/) |

> ⚠️ kabuステーションは **Windows 専用**です。Linux・Mac では動作しません。

---

## B-1. Core 機能の導入（必須手順）

### B-1-1. リポジトリのクローン

```powershell
# プロジェクトを配置したいディレクトリで実行
git clone https://github.com/your-org/KabuSys.git
cd KabuSys
```

### B-1-2. 仮想環境の構築と依存パッケージのインストール

```powershell
# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化（PowerShell）
.venv\Scripts\Activate.ps1

# 依存パッケージをインストール
pip install -e .
```

> ⚠️ PowerShell でスクリプト実行が禁止されている場合は、管理者権限で以下を実行してください。
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### B-1-3. 環境設定ウィザードで `.env` を作成

KabuSys は `.env` ファイルに API キーや動作モードなどの設定を保存します。
対話式のウィザードで自動生成できます。

```powershell
python -m kabusys.config_setup
```

ウィザードの質問に回答すると、プロジェクトルートに `.env` が生成されます。

**設定区分の凡例:**

| ラベル | 意味 |
|---|---|
| Core 必須 | Core を動かすために必要な設定 |
| Core 任意 | Core が使う設定だが、未設定でもデフォルト値で Core は動作する |
| Addon 任意 | Addon 導入時のみ意味をもつ設定。未設定でも Core の自動売買フローには影響しない |

**Core 必須設定:**

| 環境変数 | 説明 | 例 |
|---|---|---|
| `KABUSYS_ENV` | 実行モード | `paper_trading`（テスト）/ `live`（本番） |
| `JQUANTS_BULK_API_KEY` | J-Quants v2 API キー | `your_api_key` |
| `KABU_API_PASSWORD` | kabuステーション API パスワード（本番用） | `your_api_password` |

> ℹ️ J-Quants API v2 では、リフレッシュトークン／ID トークンは不要です。API キー（`JQUANTS_BULK_API_KEY`）のみで全エンドポイントを利用できます。

**Core 任意設定:**（未設定でもデフォルト値で Core は動作します）

| 環境変数 | 説明 | デフォルト |
|---|---|---|
| `PAPER_FILL_MODE` | ペーパートレードの約定方式（`instant`/`partial`/`never`/`reject`） | `instant` |
| `PAPER_TRADING_INITIAL_CASH` | MockBrokerClient の初期仮想資金（円） | `10000000` |
| `KABU_USE_SANDBOX` | `true` でポート 18081 のkabu検証環境を使用（`paper_trading` 時のみ有効） | `false` |
| `KABU_SANDBOX_API_PASSWORD` | kabu検証環境用 API パスワード（`KABU_USE_SANDBOX=true` 時） | （空） |
| `LOG_LEVEL` | ログの詳細レベル | `INFO` |

**Addon 任意設定:**（未設定でも Core の自動売買フローには影響しません）

| 環境変数 | 区分 | 説明 | デフォルト |
|---|---|---|---|
| `LINE_NOTIFY_ENABLED` | Notification Addon | LINE 通知の有効化 | `false` |
| `ENABLE_AI_SENTIMENT` | AI Addon | AI センチメントの有効化 | `false` |
| `OPENAI_API_KEY` | AI Addon | OpenAI API キー（`ENABLE_AI_SENTIMENT=true` 時に必須） | （空） |
| `ENABLE_TDNET` | Disclosure Addon | TDnet 適時開示収集の有効化 | `false` |
| `ENABLE_EDINET` | Disclosure Addon | EDINET 法定開示収集の有効化 | `false` |
| `EDINET_API_KEY` | Disclosure Addon | EDINET API サブスクリプションキー（`ENABLE_EDINET=true` 時に必須） | （空） |
| `ENABLE_YAHOONEWS` | News Addon | Yahoo News RSS 収集の有効化 | `false` |

### B-1-4. 設定の検証

`.env` を作成したら、設定に問題がないかを必ず確認します。

```powershell
python -m kabusys.validate_config
```

**正常な出力例:**
```
[OK] KABUSYS_ENV = paper_trading
[OK] JQUANTS_BULK_API_KEY: 設定済み
[OK] risk_config.yaml: 読み込み成功
...
すべての検証が完了しました。
```

エラーが表示された場合は、`.env` の該当項目を修正してください。

### B-1-5. データベースの初期化

```powershell
# 本番用 DB の初期化
python scripts/setup_db.py

# ペーパートレード用 DB も合わせて初期化
python scripts/setup_db.py --paper
```

### B-1-6. 初期市場データの取り込み（J-Quants Bootstrap）

KabuSys を初めて起動する前に、J-Quants Bulk Download API から過去の株価・財務・銘柄マスタ・カレンダーを DuckDB に取り込む必要があります。

> ⚠️ Bulk Download API は **J-Quants Standard プラン以上**が必要です。Free/Light プランではこの手順を実行できません。

```powershell
# まずドライランで取得件数を確認
python -m kabusys.data.bootstrap --dry-run

# 全エンドポイントを一括取得（初回は数分〜数十分かかります）
# 途中で中断しても続きから再実行できます
python -m kabusys.data.bootstrap

# 特定エンドポイントのみ取得する場合
python -m kabusys.data.bootstrap --endpoint /equities/bars/daily

# 最初からやり直す場合（履歴・ローカルキャッシュを全削除）
python -m kabusys.data.bootstrap --fresh --yes

# ローカルの .gz ファイルだけを処理する場合（API を呼ばずオフライン投入）
python -m kabusys.data.bootstrap --local

# データテーブルを全削除してから再インポートする場合（ローカルファイルは保持）
python -m kabusys.data.bootstrap --truncate --yes

# 詳細ログを表示する場合
python -m kabusys.data.bootstrap --verbose
```

> ℹ️ `--local` モードでは `data/bootstrap/raw/` 内の `.gz` ファイルを対象にします。サブディレクトリ形式（`raw/equities/bars/daily/*.gz`）とフラット形式（`raw/equities_bars_daily_*.gz`）の両方に対応しています。月次ファイルと日次ファイルが同じ日付を含む場合でも `ON CONFLICT DO UPDATE` により DB 上の重複行は発生しません。

**取得対象エンドポイント（Standard プラン）:**

| エンドポイント | 内容 |
|---|---|
| `/equities/bars/daily` | 日足株価（OHLCV） |
| `/equities/master` | 銘柄マスタ |
| `/fins/summary` | 財務サマリー |
| `/markets/calendar` | 取引カレンダー |
| `/indices/bars/daily/topix` | TOPIX 日足 |

Bootstrap 後、Core の処理フローを一度手動実行してデータが正しく処理されるか確認します。

```powershell
# Core 標準フロー（必須確認）
python scripts/run_feature_gen.py
python scripts/run_strategy_signal.py
python scripts/run_portfolio_construction.py

# AI Addon（ENABLE_AI_SENTIMENT=true のときのみ）
# python scripts/run_ai_analysis.py
```

### B-1-7. Task Scheduler の設定（夜間バッチの自動化）

KabuSys は引け後〜翌朝にかけて複数のバッチ処理を自動実行します。
Windows タスクスケジューラに登録することで、毎日自動で動きます。

```powershell
# Task Scheduler への自動登録
powershell -File scripts\setup_task_scheduler.ps1
```

**Core 標準ジョブ一覧:**

| 時刻 | 処理 | スクリプト |
|---|---|---|
| 15:30 | 市場データ更新 | `scripts/run_data_update.py` |
| 16:00 | 特徴量計算 | `scripts/run_feature_gen.py` |
| 20:00 | 売買シグナル生成 | `scripts/run_strategy_signal.py` |
| 21:00 | ポートフォリオ構築 | `scripts/run_portfolio_construction.py` |
| 21:15 | 夜間バッチ結果レポート | `scripts/run_night_batch_report.py` |
| 08:30 | Execution Engine 起動 | `python -m kabusys.run_execution` |
| 09:00 | Monitoring 起動 | `python -m kabusys.run_monitoring` |

**Addon 有効時のみ動くジョブ一覧:**（未設定でも Core の売買フローには影響しません）

| 時刻 | 処理 | Addon | スクリプト |
|---|---|---|---|
| 15:33 | Yahoo News RSS 収集 | News Addon（`ENABLE_YAHOONEWS=true`） | `scripts/run_yahoonews_collection.py` |
| 15:35 | TDnet 適時開示収集 | Disclosure Addon（`ENABLE_TDNET=true`） | `scripts/run_tdnet_collection.py` |
| 15:40 | EDINET 法定開示収集 | Disclosure Addon（`ENABLE_EDINET=true`） | `scripts/run_edinet_collection.py` |
| 17:00 | 開示イベント分類 | Disclosure Addon（`ENABLE_TDNET=true`） | `scripts/run_disclosure_classification.py` |
| 18:00 | AI 分析 | AI Addon（`ENABLE_AI_SENTIMENT=true`） | `scripts/run_ai_analysis.py` |

> 詳細は `documents/10_Runtime/RuntimeJobSchedule.md` を参照してください。

> **補足:** `pre_market_report`（08:00）および `market_close_report`（15:00）は Task Scheduler の自動ジョブではなく、オペレーターが手動で実行するコマンドです（`python -m kabusys.run_pre_market_report`、`python -m kabusys.run_market_close_report`）。詳細は [D_LiveOperation.md](./D_LiveOperation.md) を参照してください。

---

## B-2. Addon 機能の有効化

Addon 機能は `.env` の設定を変更するだけで有効化できます。
Core の自動売買フローに影響なくいつでも追加・削除できます。

### B-2-1. LINE 通知の設定（Notification Addon — 任意）

LINE 通知を使うと、発注・約定・エラーなどの重要なイベントをスマホの LINE で受け取れます。

**必要なもの:**
- LINE 公式アカウント（Messaging API チャネル）
- チャネルアクセストークン
- 通知を受け取る LINE ユーザー ID

**`.env` に以下を追加:**

```env
LINE_NOTIFY_ENABLED=true
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_USER_ID=your_line_user_id
```

設定後、`python -m kabusys.validate_config` で検証します。

### B-2-2. AI センチメント分析の設定（AI Addon — 任意）

Yahoo ニュースの記事を OpenAI が自動的に読み取り、各銘柄の市場センチメント（強気・弱気）をスコア化して売買判断に加味します（最大 10% の影響）。

**Core-only モード（`ENABLE_AI_SENTIMENT=false`、デフォルト）について:**

`ENABLE_AI_SENTIMENT=false` のとき、システムは Core-only モードで動作します。このモードでは:
- AI センチメントスコア（`ai_scores`）は参照しません
- レジーム判定は `NullRegimeProvider` が使用され、常に `'bull'`（非 Bear）として扱います
- Bear レジームフィルタは発動せず、全銘柄が BUY 候補になります
- Core の自動売買フロー・バックテストは AI データなしで完全に動作します

**他の Addon との依存関係:**

> AI Addon は、ニュース原文（`raw_news`）の入力として **News Addon**（`ENABLE_YAHOONEWS=true`）または **Disclosure Addon**（`ENABLE_TDNET=true`）との併用を推奨します。いずれのニュースソースも有効でない場合、AI 分析バッチは入力データなしで実行され、`ai_scores` は空（0件）になります。その場合でも Core の自動売買フローはスキップなしで正常に動作します（ニューススコアはデフォルト値で補完されます）。

**必要なもの:**
- OpenAI API キー（有料・従量課金）

> ⚠️ AI センチメントの有効化は **OpenAI API の利用料金が発生します**。有効化前に利用コストを確認してください。

**`.env` に以下を追加:**

```env
ENABLE_AI_SENTIMENT=true
OPENAI_API_KEY=sk-...
```

### B-2-3. TDnet 適時開示収集の設定（Disclosure Addon — 任意）

TDnet（適時開示情報閲覧サービス）から当日の開示一覧を自動収集し、決算短信・業績修正・自己株取得などのイベントを分類・スコア化します。

**必要なもの:**
- 特になし（無料で利用可能）

**`.env` に以下を追加:**

```env
ENABLE_TDNET=true
```

有効化すると以下の2ジョブが毎日自動実行されます。

| 時刻 | 処理 | 保存先 |
|---|---|---|
| 15:35 | TDnet から当日の開示一覧を取得・保存 | `raw_disclosures` |
| 17:00 | 開示タイトルを分類してイベントスコアを付与 | `disclosure_events` |

> ℹ️ `ENABLE_TDNET=false`（デフォルト）の場合、両ジョブは即座にスキップされ Core 機能（自動売買）に影響しません。

### B-2-4. EDINET 法定開示収集の設定（Disclosure Addon — 任意）

EDINET（Electronic Disclosure for Investors' NETwork）API から有価証券報告書・四半期報告書・大量保有報告書などの法定開示を自動収集します。TDnet では取得できない開示書類の補完層として機能します。

**必要なもの:**
- EDINET API サブスクリプションキー（無料、要登録）

**取得先:** [https://disclosure2.edinet-fsa.go.jp/](https://disclosure2.edinet-fsa.go.jp/)

**`.env` に以下を追加:**

```env
ENABLE_EDINET=true
EDINET_API_KEY=your_subscription_key
```

有効化すると以下のジョブが毎日自動実行されます。

| 時刻 | 処理 | 保存先 |
|---|---|---|
| 15:40 | EDINET から当日の法定開示一覧を取得・保存 | `raw_disclosures`（source='edinet'） |

**収集対象書類種別:**
- 有価証券報告書（120）
- 四半期報告書（130）
- 臨時報告書（140）/ 訂正臨時報告書（150）
- 大量保有報告書（170/171/172）

> ℹ️ `ENABLE_EDINET=false`（デフォルト）の場合、ジョブは即座にスキップされ Core 機能（自動売買）に影響しません。`ENABLE_EDINET=true` かつ `EDINET_API_KEY` 未設定の場合はエラーログを出力してジョブが終了します。

---

### B-2-5. Yahoo News RSS 収集の設定（News Addon — 任意）

Yahoo News（ビジネスカテゴリ）の RSS フィードから当日のニュースを収集し、`raw_news` テーブルへ保存します。AI センチメント分析（`ENABLE_AI_SENTIMENT=true`）の前段データソースとして機能します。

**必要なもの:**
- なし（無料、API キー不要）

**`.env` に追記:**

```env
ENABLE_YAHOONEWS=true
```

**実行タイミング:**

| 時刻 | 処理 | 保存先 |
|---|---|---|
| 15:33 | Yahoo News RSS から当日ニュースを取得・保存 | `raw_news` |

**注意:**
- AI センチメントスコアリング（`raw_news` → `ai_scores`）は `ENABLE_AI_SENTIMENT=true` を別途設定する必要があります
- 銘柄コードとのリンク付けは `stocks` テーブルを参照します（テーブルが空の場合はリンクをスキップ）

> ℹ️ `ENABLE_YAHOONEWS=false`（デフォルト）の場合、ジョブは即座にスキップされ Core 機能（自動売買）に影響しません。

---

## B-3. 導入完了チェックリスト

### Core セットアップ完了チェック

ここまで通れば Core は使い始められます。

- [ ] `python -m kabusys.validate_config` がエラーなく完了する
- [ ] `python scripts/setup_db.py` で `data/kabusys.duckdb` と `data/monitoring.db` が作成されている
- [ ] `python scripts/setup_db.py --paper` で `data/paper_trading.db` が作成されている
- [ ] DuckDB に市場データ（`prices_daily`, `stocks` など）が存在する
- [ ] Task Scheduler に Core 標準ジョブが登録されている
- [ ] `.env` に `KABUSYS_ENV=paper_trading` が設定されている
- [ ] `python -m kabusys.run_pre_market_report` が正常に動作する
- [ ] `python -m kabusys.run_execution`（別ターミナルで起動）が起動エラーなく動く

### Addon 有効化時の追加チェック

（各 Addon を有効化した場合のみ確認します。未設定でも Core は動作します）

- [ ] LINE 通知（Notification Addon）: テストメッセージが LINE に届く
- [ ] AI センチメント（AI Addon）: `ENABLE_AI_SENTIMENT=true` で AI 分析バッチが正常完了する
- [ ] TDnet 収集（Disclosure Addon）: `ENABLE_TDNET=true` で `run_tdnet_collection.py` が正常完了する
- [ ] EDINET 収集（Disclosure Addon）: `ENABLE_EDINET=true` で `run_edinet_collection.py` が正常完了する
- [ ] Yahoo News 収集（News Addon）: `ENABLE_YAHOONEWS=true` で `run_yahoonews_collection.py` が正常完了する

---

## 次のステップ

導入が完了したら、まずはペーパートレードで動作を確認することをお勧めします。

→ [C_PaperTrading.md — テスト運用（ペーパートレード）の手順](./C_PaperTrading.md)
